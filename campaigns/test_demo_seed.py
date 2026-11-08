import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.db import IntegrityError, DatabaseError, connection
from accounts.models import User
from campaigns.models import Campaign, Tag, Donation, CampaignRating, Comment
from campaigns.management.commands.seed_demo_campaigns import Command as SeedCommand


import io
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, DatabaseError, connection
from accounts.models import User
from campaigns.models import Campaign, Tag, Donation, CampaignRating, Comment
from campaigns.management.commands.seed_demo_campaigns import Command as SeedCommand


class DemoCampaignSeedCommandTests(TestCase):
    def test_seed_empty_database(self):
        """Test seeding into an empty database creates exactly 7 campaigns and related records."""
        call_command('seed_demo_campaigns')

        self.assertEqual(Campaign.objects.count(), 7)
        self.assertEqual(Tag.objects.count(), 4)
        self.assertEqual(Donation.objects.count(), 14)
        self.assertEqual(CampaignRating.objects.count(), 2)
        self.assertEqual(Comment.objects.count(), 3)

        # Verify key campaign IDs
        expected_ids = {1, 10, 192, 193, 194, 195, 196}
        self.assertEqual(set(Campaign.objects.values_list('id', flat=True)), expected_ids)

        # Verify campaign statuses
        completed_c = Campaign.objects.get(id=1)
        self.assertEqual(completed_c.status, 'Completed')
        self.assertEqual(completed_c.raised_amount, Decimal('300000000.00'))

        active_c = Campaign.objects.get(id=10)
        self.assertEqual(active_c.status, 'Active')
        self.assertEqual(active_c.raised_amount, Decimal('6001.01'))

    def test_no_force_option_exists(self):
        """Test that --force argument is completely removed from command parser."""
        cmd = SeedCommand()
        parser = cmd.create_parser('manage.py', 'seed_demo_campaigns')
        action_destinations = [action.dest for action in parser._actions]
        self.assertNotIn('force', action_destinations)

        # Calling call_command with force=True must raise TypeError
        with self.assertRaises(TypeError) as ctx:
            call_command('seed_demo_campaigns', force=True)
        self.assertIn("Unknown option(s) for seed_demo_campaigns command: force", str(ctx.exception))

    def test_repeated_execution_without_duplicates_and_idempotence(self):
        """Test that running the command multiple times does not duplicate records (clean idempotence)."""
        call_command('seed_demo_campaigns')
        self.assertEqual(Campaign.objects.count(), 7)

        # Run second time: safely skipped with [ALREADY SEEDED]
        stdout_capture = io.StringIO()
        call_command('seed_demo_campaigns', stdout=stdout_capture)
        self.assertEqual(Campaign.objects.count(), 7)
        self.assertEqual(Donation.objects.count(), 14)
        self.assertIn('[ALREADY SEEDED]', stdout_capture.getvalue())

        # Run third time: same safe skip
        call_command('seed_demo_campaigns')
        self.assertEqual(Campaign.objects.count(), 7)
        self.assertEqual(Donation.objects.count(), 14)
        self.assertEqual(Tag.objects.count(), 4)

    def test_subsequent_container_startups_succeed_cleanly(self):
        """Simulate container restart where INIT_DEMO_DATA=true remains enabled."""
        call_command('seed_demo_campaigns')
        self.assertEqual(Campaign.objects.count(), 7)

        # Subsequent container start (must not crash, must not duplicate)
        try:
            call_command('seed_demo_campaigns')
        except Exception as e:
            self.fail(f'Subsequent startup failed unexpectedly: {e}')

        self.assertEqual(Campaign.objects.count(), 7)
        self.assertEqual(Donation.objects.count(), 14)

    def test_existing_records_with_fixture_ids_never_overwritten(self):
        """
        Test that if a production record coincidentally has the same ID as a fixture record
        (e.g. ID=1 with a different title), seeding strictly aborts and never overwrites it.
        """
        owner = User.objects.create(email='prod_owner@example.com', first_name='ProdOwner', is_active=True)
        Campaign.objects.create(
            id=1,
            owner=owner,
            title='Production Campaign Coincidentally Using ID 1',
            story='Production story that must never be modified or overwritten.',
            target_amount=Decimal('50000.00'),
            case_type='Normal',
            status='Active'
        )

        stderr_capture = io.StringIO()
        call_command('seed_demo_campaigns', stderr=stderr_capture)

        # Must report safety abort in stderr
        self.assertIn('[SAFETY ABORT]', stderr_capture.getvalue())

        # Existing record must remain 100% untouched
        self.assertEqual(Campaign.objects.count(), 1)
        campaign = Campaign.objects.get(id=1)
        self.assertEqual(campaign.title, 'Production Campaign Coincidentally Using ID 1')
        self.assertEqual(campaign.owner.email, 'prod_owner@example.com')

    def test_conflicting_tags_cause_safe_abort(self):
        """Test that if a tag slug matches but has a conflicting name, seeding safely aborts."""
        Tag.objects.create(name='Alternative Medical Name', slug='medical')

        stderr_capture = io.StringIO()
        call_command('seed_demo_campaigns', stderr=stderr_capture)

        self.assertIn('[SAFETY ABORT]', stderr_capture.getvalue())
        self.assertIn('Tag slug conflict detected for slug "medical"', stderr_capture.getvalue())

        # Database must not have been modified with campaigns
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(Tag.objects.get(slug='medical').name, 'Alternative Medical Name')

    def test_conflicting_related_records_cause_safe_abort(self):
        """Test that non-empty related tables (e.g. pre-existing donations) cause a safe abort."""
        owner = User.objects.create(email='donor_user@example.com', first_name='DonorUser', is_active=True)
        c = Campaign.objects.create(
            id=777,
            owner=owner,
            title='Protected Campaign',
            story='Story',
            target_amount=Decimal('1000.00'),
            case_type='Normal',
            status='Active'
        )
        Donation.objects.create(
            id=777,
            campaign=c,
            amount=Decimal('100.00'),
            donor_name='Live Donor',
            donor_email='donor@prod.com'
        )

        stderr_capture = io.StringIO()
        call_command('seed_demo_campaigns', stderr=stderr_capture)

        self.assertIn('[SAFETY ABORT]', stderr_capture.getvalue())
        # Only the 1 existing production campaign and donation must exist
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Donation.objects.count(), 1)

    def test_existing_user_passwords_and_roles_never_altered(self):
        """Verify that existing user credentials, permissions, and roles are never altered by seeding."""
        user = User.objects.create(
            email='demo@egystory.com',
            first_name='Original',
            is_active=True,
            is_staff=True,
            is_superuser=False
        )
        user.set_password('SuperSecretUserPassword123!')
        user.save()

        call_command('seed_demo_campaigns')

        # Refresh from database and assert password and staff role remain 100% valid and untouched
        user.refresh_from_db()
        self.assertTrue(user.check_password('SuperSecretUserPassword123!'))
        self.assertEqual(user.first_name, 'Original')
        self.assertTrue(user.is_staff)

    def test_related_records_and_foreign_key_integrity(self):
        """Test that foreign-key relationships and M2M tags are fully validated and intact."""
        call_command('seed_demo_campaigns')

        # Check multi-tag association on Campaign 193
        c193 = Campaign.objects.get(id=193)
        tag_slugs = set(c193.tags.values_list('slug', flat=True))
        self.assertIn('emergency', tag_slugs)
        self.assertIn('medical', tag_slugs)

        # Check creator user safety
        for campaign in Campaign.objects.all():
            self.assertIsNotNone(campaign.owner)
            self.assertTrue(campaign.owner.is_active)

        # Check donations point to valid campaigns
        for donation in Donation.objects.all():
            self.assertIn(donation.campaign.id, {1, 10})

    def test_post_seed_new_record_creation_without_pk_conflicts(self):
        """
        Verify that after seeding explicit primary keys, creating NEW models
        without specifying IDs succeeds without duplicate-key / sequence conflicts.
        """
        call_command('seed_demo_campaigns')

        user = User.objects.get(email='demo@egystory.com')

        # Create new Campaign without specifying ID
        new_campaign = Campaign.objects.create(
            title='Brand New User Campaign',
            story='Created by a user after demo seeding.',
            owner=user,
            target_amount=Decimal('5000.00'),
            case_type='Normal',
            status='Active',
        )
        self.assertIsNotNone(new_campaign.id)
        self.assertNotIn(new_campaign.id, {1, 10, 192, 193, 194, 195, 196})

        # Create new Donation without specifying ID
        new_donation = Donation.objects.create(
            campaign=new_campaign,
            donor_name='New Donor',
            donor_email='newdonor@example.com',
            amount=Decimal('250.00'),
            is_anonymous=False,
        )
        self.assertIsNotNone(new_donation.id)

        # Create new Rating without specifying ID
        new_rating = CampaignRating.objects.create(
            campaign=new_campaign,
            user=user,
            score=5,
        )
        self.assertIsNotNone(new_rating.id)

        # Create new Comment without specifying ID
        new_comment = Comment.objects.create(
            campaign=new_campaign,
            user=user,
            content='Great new story!',
        )
        self.assertIsNotNone(new_comment.id)

    def test_postgresql_sequence_reset_logic(self):
        """Verify the database sequence reset logic executes SQL correctly for PostgreSQL."""
        cmd = SeedCommand()
        mock_cursor = MagicMock()

        with patch.object(connection.ops, 'sequence_reset_sql', return_value=[
            'SELECT setval(\'"campaigns_campaign_id_seq"\', 196, true);',
            'SELECT setval(\'"campaigns_donation_id_seq"\', 14, true);',
        ]):
            with patch.object(connection, 'cursor') as mock_cursor_ctx:
                mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
                cmd._reset_database_sequences([Campaign, Donation])

                # Verify both sequence reset queries were executed
                self.assertEqual(mock_cursor.execute.call_count, 2)
                mock_cursor.execute.assert_any_call('SELECT setval(\'"campaigns_campaign_id_seq"\', 196, true);')
                mock_cursor.execute.assert_any_call('SELECT setval(\'"campaigns_donation_id_seq"\', 14, true);')

    def test_missing_media_handling(self):
        """Test that missing media files trigger a diagnostic warning without crashing the seed."""
        sample_fixture = {
            'tags': [{'name': 'TestTag', 'slug': 'testtag'}],
            'users': [{'email': 'creator@test.com', 'first_name': 'Test'}],
            'campaigns': [{
                'id': 555,
                'title': 'Missing Media Campaign',
                'story': 'Testing media validation warning.',
                'owner_email': 'creator@test.com',
                'target_amount': '5000.00',
                'initial_raised_amount': '0.00',
                'raised_amount': '0.00',
                'campaign_image': 'campaigns/definitely_nonexistent_image_12345.jpg',
                'case_type': 'Normal',
                'status': 'Active',
                'tags': ['testtag']
            }],
            'donations': [],
            'ratings': [],
            'comments': []
        }

        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as tf:
            json.dump(sample_fixture, tf)
            temp_path = tf.name

        try:
            call_command('seed_demo_campaigns', fixture=temp_path)
            self.assertTrue(Campaign.objects.filter(id=555).exists())
        finally:
            Path(temp_path).unlink(missing_ok=True)


class DemoCampaignSeedRollbackTests(TransactionTestCase):
    def test_transaction_rollback_on_failure(self):
        """Test that if an error occurs midway, the entire database transaction is rolled back."""
        original_create = Campaign.objects.create

        def mock_create(*args, **kwargs):
            if kwargs.get('id') == 192:
                raise IntegrityError('Simulated database integrity failure during campaign creation.')
            return original_create(*args, **kwargs)

        with patch.object(Campaign.objects, 'create', side_effect=mock_create):
            with self.assertRaises(IntegrityError):
                call_command('seed_demo_campaigns')

        # Transaction rollback must ensure ZERO campaigns exist
        self.assertEqual(Campaign.objects.count(), 0)

    def test_sequence_reset_failure_propagates_and_rolls_back_transaction(self):
        """Test that sequence reset failure propagates, raising an exception and rolling back all inserts."""
        with patch.object(connection.ops, 'sequence_reset_sql', return_value=['SELECT 1;']):
            with patch.object(connection, 'cursor', side_effect=DatabaseError('Simulated sequence reset fatal error')):
                with self.assertRaises(DatabaseError):
                    call_command('seed_demo_campaigns')

        # Since sequence reset failed, transaction MUST be rolled back: zero campaigns exist
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(Tag.objects.count(), 0)
