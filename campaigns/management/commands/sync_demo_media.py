import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


class Command(BaseCommand):
    help = 'Ensures permanent demo media files exist in the configured storage (local or cloud).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing files in target storage.',
        )

    def handle(self, *args, **options):
        demo_media_dir = getattr(settings, 'DEMO_MEDIA_ROOT', settings.BASE_DIR / 'demo_media')
        if not os.path.exists(demo_media_dir):
            self.stdout.write(self.style.WARNING(f'Demo media directory not found at: {demo_media_dir}'))
            return

        force = options['force']
        synced_count = 0
        skipped_count = 0

        self.stdout.write(f'Scanning demo media from: {demo_media_dir}...')

        for root, _, files in os.walk(demo_media_dir):
            for filename in files:
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(demo_media_dir).as_posix()

                exists = default_storage.exists(rel_path)
                if exists and not force:
                    skipped_count += 1
                    continue

                if exists and force:
                    try:
                        default_storage.delete(rel_path)
                    except Exception:
                        pass

                with open(full_path, 'rb') as f:
                    content = f.read()
                    default_storage.save(rel_path, ContentFile(content))
                    synced_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Synced: {rel_path}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Demo media sync completed: {synced_count} file(s) synced, {skipped_count} skipped.'
            )
        )

