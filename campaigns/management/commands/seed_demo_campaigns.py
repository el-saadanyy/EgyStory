import json
import logging
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.color import no_style
from django.utils.dateparse import parse_datetime, parse_date
from accounts.models import User
from campaigns.models import Campaign, Tag, Donation, CampaignRating, Comment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Safely and idempotently seeds the 7 curated portfolio demo campaigns into an empty database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture',
            default=str(settings.BASE_DIR / 'fixtures' / 'demo_campaigns.json'),
            help='Path to the demo campaigns JSON fixture.',
        )

    def _reset_database_sequences(self, models_list):
        """
        Ensures auto-increment sequences (e.g. PostgreSQL pg_get_serial_sequence)
        are synchronized to MAX(id) after bulk seeding explicit primary keys.
        Any failure during sequence synchronization raises directly and aborts
        the enclosing atomic transaction.
        """
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), models_list)
        if sequence_sql:
            with connection.cursor() as cursor:
                for line in sequence_sql:
                    cursor.execute(line)
            self.stdout.write(self.style.NOTICE(f'  [SEQUENCES] Synchronized {len(sequence_sql)} database auto-increment sequence(s).'))

    def handle(self, *args, **options):
        fixture_path = Path(options['fixture'])

        self.stdout.write(self.style.NOTICE('\n=== EgyStory Demo Campaigns Seeding ==='))

        if not fixture_path.exists():
            raise CommandError(f'Demo fixture file not found at: {fixture_path}')

        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        fixture_campaigns = data.get('campaigns', [])
        fixture_campaign_count = len(fixture_campaigns)
        fixture_campaign_map = {c['id']: c['title'] for c in fixture_campaigns}

        # Check existing table counts
        campaign_count = Campaign.objects.count()
        donation_count = Donation.objects.count()
        rating_count = CampaignRating.objects.count()
        comment_count = Comment.objects.count()

        # 1. Check for conflicting tags
        for t_item in data.get('tags', []):
            existing_tag = Tag.objects.filter(slug=t_item['slug']).first()
            if existing_tag and existing_tag.name != t_item['name']:
                self.stderr.write(
                    self.style.ERROR(
                        f'  [SAFETY ABORT] Tag slug conflict detected for slug "{t_item["slug"]}". '
                        f'Existing name: "{existing_tag.name}", Fixture name: "{t_item["name"]}". '
                        f'Seeding aborted to prevent altering production data.\n'
                    )
                )
                return

        # 2. Case: Database already contains the exact previously seeded demo dataset
        if campaign_count == fixture_campaign_count:
            all_match = True
            for c_id, expected_title in fixture_campaign_map.items():
                if not Campaign.objects.filter(id=c_id, title=expected_title).exists():
                    all_match = False
                    break

            if all_match:
                self.stdout.write(
                    self.style.NOTICE(
                        f'  [ALREADY SEEDED] Database already contains the exact demo dataset '
                        f'({campaign_count} campaigns). Seeding safely skipped without modifications.\n'
                    )
                )
                return

        # 3. Case: Database is non-empty and does NOT match the exact demo dataset
        if campaign_count > 0 or donation_count > 0 or rating_count > 0 or comment_count > 0:
            self.stderr.write(
                self.style.ERROR(
                    f'  [SAFETY ABORT] Database contains existing conflicting or non-demo records '
                    f'(Campaigns: {campaign_count}, Donations: {donation_count}, '
                    f'Ratings: {rating_count}, Comments: {comment_count}). '
                    f'Seeding aborted to prevent modifying production data.\n'
                )
            )
            return

        # 4. Case: Tables are clean/empty -> Proceed with seeding
        demo_media_dir = getattr(settings, 'DEMO_MEDIA_ROOT', settings.BASE_DIR / 'demo_media')

        stats = {
            'tags_created': 0, 'tags_skipped': 0,
            'users_created': 0, 'users_skipped': 0,
            'campaigns_created': 0,
            'donations_created': 0,
            'ratings_created': 0,
            'comments_created': 0,
            'media_missing': 0,
        }

        try:
            with transaction.atomic():
                # Step 1: Seed Tags
                tag_cache = {}
                for tag_item in data.get('tags', []):
                    tag, created = Tag.objects.get_or_create(
                        slug=tag_item['slug'],
                        defaults={'name': tag_item['name']},
                    )
                    tag_cache[tag_item['slug']] = tag
                    if created:
                        stats['tags_created'] += 1
                    else:
                        stats['tags_skipped'] += 1

                # Step 2: Seed / Resolve Users safely (never overwrite existing passwords or permissions)
                user_cache = {}
                for user_item in data.get('users', []):
                    email = user_item['email'].lower().strip()
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'first_name': user_item.get('first_name', ''),
                            'last_name': user_item.get('last_name', ''),
                            'phone': user_item.get('phone', '01000000000'),
                            'is_active': True,
                            'is_staff': False,
                            'is_superuser': False,
                        }
                    )
                    if created:
                        user.set_unusable_password()
                        user.save()
                        stats['users_created'] += 1
                    else:
                        # Existing user: strictly zero mutations
                        stats['users_skipped'] += 1
                    user_cache[email] = user

                # Ensure default demo user exists in cache as fallback
                fallback_user = user_cache.get('demo@egystory.com') or User.objects.filter(is_active=True).first()
                if not fallback_user:
                    fallback_user = User.objects.create(
                        email='demo@egystory.com',
                        first_name='Demo',
                        last_name='User',
                        phone='01000000001',
                        is_active=True,
                    )
                    fallback_user.set_unusable_password()
                    fallback_user.save()
                    user_cache['demo@egystory.com'] = fallback_user

                # Step 3: Seed Campaigns
                campaign_cache = {}
                for c_item in data.get('campaigns', []):
                    c_id = c_item['id']
                    owner_email = c_item.get('owner_email', '').lower().strip()
                    owner = user_cache.get(owner_email, fallback_user)

                    # Validate referenced media
                    img_path = c_item.get('campaign_image', '')
                    if img_path:
                        local_demo_img = demo_media_dir / img_path
                        storage_has_img = default_storage.exists(img_path)
                        if not storage_has_img and not local_demo_img.exists():
                            stats['media_missing'] += 1
                            self.stdout.write(
                                self.style.WARNING(f'  [MEDIA NOTICE] Image not yet synced to storage: {img_path}')
                            )

                    deadline_val = parse_date(c_item['deadline']) if c_item.get('deadline') else None
                    created_at_val = parse_datetime(c_item['created_at']) if c_item.get('created_at') else None

                    campaign = Campaign.objects.create(
                        id=c_id,
                        owner=owner,
                        title=c_item['title'],
                        story=c_item['story'],
                        target_amount=Decimal(c_item['target_amount']),
                        initial_raised_amount=Decimal(c_item.get('initial_raised_amount', '0.00')),
                        raised_amount=Decimal(c_item.get('raised_amount', '0.00')),
                        campaign_image=img_path,
                        case_type=c_item['case_type'],
                        status=c_item['status'],
                        is_featured=c_item.get('is_featured', False),
                        is_manual_critical=c_item.get('is_manual_critical', False),
                        deadline=deadline_val,
                    )

                    if created_at_val:
                        Campaign.objects.filter(id=c_id).update(created_at=created_at_val)
                    stats['campaigns_created'] += 1

                    # Attach tags
                    tags_to_set = [tag_cache[ts] for ts in c_item.get('tags', []) if ts in tag_cache]
                    if tags_to_set:
                        campaign.tags.set(tags_to_set)

                    campaign_cache[c_id] = campaign

                # Step 4: Seed Donations
                for d_item in data.get('donations', []):
                    c_id = d_item['campaign_id']
                    campaign = campaign_cache.get(c_id) or Campaign.objects.filter(id=c_id).first()
                    if not campaign:
                        continue

                    d_id = d_item.get('id')
                    created_at_val = parse_datetime(d_item['created_at']) if d_item.get('created_at') else None

                    donation = Donation.objects.create(
                        id=d_id,
                        campaign=campaign,
                        donor_name=d_item.get('donor_name', ''),
                        donor_email=d_item.get('donor_email', ''),
                        amount=Decimal(d_item['amount']),
                        is_anonymous=d_item.get('is_anonymous', False),
                    )

                    if created_at_val and d_id:
                        Donation.objects.filter(id=d_id).update(created_at=created_at_val)
                    stats['donations_created'] += 1

                # Step 5: Seed Ratings
                for r_item in data.get('ratings', []):
                    c_id = r_item['campaign_id']
                    campaign = campaign_cache.get(c_id) or Campaign.objects.filter(id=c_id).first()
                    user = user_cache.get(r_item.get('user_email', '').lower().strip(), fallback_user)
                    if not campaign or not user:
                        continue

                    r_id = r_item.get('id')
                    CampaignRating.objects.create(
                        id=r_id,
                        campaign=campaign,
                        user=user,
                        score=r_item['score'],
                    )
                    stats['ratings_created'] += 1

                # Step 6: Seed Comments
                for c_item in data.get('comments', []):
                    c_id = c_item['campaign_id']
                    campaign = campaign_cache.get(c_id) or Campaign.objects.filter(id=c_id).first()
                    user = user_cache.get(c_item.get('user_email', '').lower().strip(), fallback_user)
                    if not campaign or not user:
                        continue

                    comm_id = c_item.get('id')
                    comment = Comment.objects.create(
                        id=comm_id,
                        campaign=campaign,
                        user=user,
                        content=c_item['content'],
                    )

                    if c_item.get('created_at') and comm_id:
                        Comment.objects.filter(id=comm_id).update(created_at=parse_datetime(c_item['created_at']))
                    stats['comments_created'] += 1

                # Step 7: Synchronize Database Sequences (failures strictly raise to abort transaction)
                self._reset_database_sequences([Tag, User, Campaign, Donation, CampaignRating, Comment])

        except Exception as e:
            logger.error(f'Demo campaigns seeding failed, transaction rolled back: {e}', exc_info=True)
            self.stderr.write(self.style.ERROR(f'\n  [ERROR] Seeding aborted: {e}\n'))
            raise

        self.stdout.write(self.style.SUCCESS('\n=== Seeding Summary ==='))
        self.stdout.write(f'  Tags:      {stats["tags_created"]} created, {stats["tags_skipped"]} skipped')
        self.stdout.write(f'  Users:     {stats["users_created"]} created, {stats["users_skipped"]} skipped')
        self.stdout.write(f'  Campaigns: {stats["campaigns_created"]} created')
        self.stdout.write(f'  Donations: {stats["donations_created"]} created')
        self.stdout.write(f'  Ratings:   {stats["ratings_created"]} created')
        self.stdout.write(f'  Comments:  {stats["comments_created"]} created')
        if stats['media_missing'] > 0:
            self.stdout.write(self.style.WARNING(f'  Media Warnings: {stats["media_missing"]} referenced images not yet in storage'))
        self.stdout.write(self.style.SUCCESS('Demo campaigns check completed successfully.\n'))
