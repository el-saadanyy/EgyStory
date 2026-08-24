"""
Management command: create_admins
Creates the 3 EgyStory admin users for Phase 1.
Safe to run multiple times (skips existing admins).
"""

from django.core.management.base import BaseCommand
from accounts.models import User


ADMINS = [
    {
        'email': 'admin1@egystory.com',
        'first_name': 'Admin',
        'last_name': 'One',
        'phone': '01012345601',
        'password': 'EgyAdmin@2026',
    },
    {
        'email': 'admin2@egystory.com',
        'first_name': 'Admin',
        'last_name': 'Two',
        'phone': '01012345602',
        'password': 'EgyAdmin@2026',
    },
    {
        'email': 'admin3@egystory.com',
        'first_name': 'Admin',
        'last_name': 'Three',
        'phone': '01012345603',
        'password': 'EgyAdmin@2026',
    },
]


class Command(BaseCommand):
    help = 'Creates the 3 EgyStory admin users for Phase 1.'

    def handle(self, *args, **options):
        self.stdout.write('\n=== EgyStory Admin Setup ===\n')

        for admin_data in ADMINS:
            email = admin_data['email']
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'  SKIP   {email} (already exists)'))
                continue

            user = User.objects.create_user(
                email=email,
                password=admin_data['password'],
                first_name=admin_data['first_name'],
                last_name=admin_data['last_name'],
                phone=admin_data['phone'],
            )
            user.is_active = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'  OK     {email}'))

        self.stdout.write('\n  Password for all admins: EgyAdmin@2026')
        self.stdout.write('  Change these passwords before going to production!\n')
