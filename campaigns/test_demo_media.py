import os
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.files.storage import default_storage


class DemoMediaSyncTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.demo_dir = Path(self.temp_dir.name) / 'demo_media'
        os.makedirs(self.demo_dir / 'campaigns', exist_ok=True)
        (self.demo_dir / 'campaigns' / 'test_sample.jpg').write_bytes(b'dummy-image-content')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sync_demo_media_command(self):
        with override_settings(DEMO_MEDIA_ROOT=self.demo_dir):
            call_command('sync_demo_media', force=True)
            self.assertTrue(default_storage.exists('campaigns/test_sample.jpg'))
            content = default_storage.open('campaigns/test_sample.jpg').read()
            self.assertEqual(content, b'dummy-image-content')
            # Clean up
            default_storage.delete('campaigns/test_sample.jpg')

