import os
from django.core.management.base import BaseCommand
from decouple import config
from accounts.models import User


class Command(BaseCommand):
    help = 'Idempotently sets up restricted demo accounts (Demo User & Demo Reviewer) for portfolio review.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            default=config('DEMO_USER_EMAIL', default='demo@egystory.com'),
            help='Email for the Demo User account.',
        )
        parser.add_argument(
            '--user-password',
            default=config('DEMO_USER_PASSWORD', default=''),
            help='Password for the Demo User account.',
        )
        parser.add_argument(
            '--reviewer-email',
            default=config('DEMO_REVIEWER_EMAIL', default='reviewer@egystory.com'),
            help='Email for the Demo Reviewer account.',
        )
        parser.add_argument(
            '--reviewer-password',
            default=config('DEMO_REVIEWER_PASSWORD', default=''),
            help='Password for the Demo Reviewer account.',
        )
        parser.add_argument(
            '--force-password',
            action='store_true',
            help='Update password even if account already exists.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\n=== EgyStory Demo Accounts Setup ==='))

        # 1. Setup Demo User
        user_email = options['user_email'].lower().strip()
        user_password = options['user_password']

        if not user_password:
            self.stdout.write(
                self.style.WARNING(
                    f'  [SKIPPED] Demo User ({user_email}): DEMO_USER_PASSWORD is not set in environment.'
                )
            )
        else:
            demo_user, created_user = User.objects.get_or_create(
                email=user_email,
                defaults={
                    'first_name': 'Demo',
                    'last_name': 'User',
                    'phone': '01000000001',
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )

            if created_user or options['force_password']:
                demo_user.set_password(user_password)
                demo_user.is_active = True
                demo_user.is_staff = False
                demo_user.is_superuser = False
                demo_user.save()
                action = 'CREATED' if created_user else 'UPDATED'
                self.stdout.write(self.style.SUCCESS(f'  [{action}] Demo User: {user_email}'))
            else:
                self.stdout.write(self.style.NOTICE(f'  [EXISTS] Demo User: {user_email} (password unchanged)'))

        # 2. Setup Demo Reviewer (Staff, strictly non-superuser)
        reviewer_email = options['reviewer_email'].lower().strip()
        reviewer_password = options['reviewer_password']

        if not reviewer_password:
            self.stdout.write(
                self.style.WARNING(
                    f'  [SKIPPED] Demo Reviewer ({reviewer_email}): DEMO_REVIEWER_PASSWORD is not set in environment.'
                )
            )
        else:
            demo_rev, created_rev = User.objects.get_or_create(
                email=reviewer_email,
                defaults={
                    'first_name': 'Demo',
                    'last_name': 'Reviewer',
                    'phone': '01000000002',
                    'is_active': True,
                    'is_staff': True,
                    'is_superuser': False,
                }
            )

            if created_rev or options['force_password']:
                demo_rev.set_password(reviewer_password)
                demo_rev.is_active = True
                demo_rev.is_staff = True
                demo_rev.is_superuser = False  # NEVER grant superuser rights
                demo_rev.save()
                action = 'CREATED' if created_rev else 'UPDATED'
                self.stdout.write(self.style.SUCCESS(f'  [{action}] Demo Reviewer: {reviewer_email}'))
            else:
                # Security safeguard: revoke superuser rights if present
                if demo_rev.is_superuser:
                    demo_rev.is_superuser = False
                    demo_rev.save(update_fields=['is_superuser'])
                self.stdout.write(self.style.NOTICE(f'  [EXISTS] Demo Reviewer: {reviewer_email} (password unchanged)'))

        self.stdout.write(self.style.SUCCESS('Demo accounts check completed.\n'))
