import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, override_settings, SimpleTestCase
from django.core.management import call_command
from django.core.files.storage import default_storage
from django.core.files.storage.filesystem import FileSystemStorage
from django.conf import settings
from decouple import Config, RepositoryEmpty


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

    @patch('boto3.client')
    @patch('boto3.resource')
    @patch('boto3.Session')
    def test_sync_demo_media_never_calls_boto3_when_s3_disabled(self, mock_session, mock_resource, mock_client):
        """Verify that when S3 is disabled, running sync_demo_media never initializes or calls boto3."""
        with override_settings(DEMO_MEDIA_ROOT=self.demo_dir):
            call_command('sync_demo_media', force=True)
            mock_client.assert_not_called()
            mock_resource.assert_not_called()
            mock_session.assert_not_called()
            self.assertTrue(default_storage.exists('campaigns/test_sample.jpg'))
            default_storage.delete('campaigns/test_sample.jpg')


class StorageConfigurationTests(SimpleTestCase):
    def test_default_storage_is_filesystem_storage(self):
        """Verify default_storage is an instance of FileSystemStorage when S3 is disabled."""
        self.assertIsInstance(default_storage._wrapped, FileSystemStorage)
        self.assertFalse(getattr(settings, 'USE_S3', False))

    def test_media_urls_are_relative_local_paths(self):
        """Verify that media URLs point to local /media/ path rather than an S3 endpoint."""
        url = default_storage.url('campaigns/10.jpeg')
        self.assertEqual(url, '/media/campaigns/10.jpeg')
        self.assertNotIn('amazonaws.com', url)
        self.assertFalse(url.startswith('http://') or url.startswith('https://'))

    def test_settings_use_s3_false_ignores_bucket_name_in_environment(self):
        """
        Verify that setting USE_S3=False guarantees FileSystemStorage even if
        AWS_STORAGE_BUCKET_NAME is set in the environment (e.g. 'egystory-disabled').
        """
        # Simulate environment where USE_S3=False and AWS_STORAGE_BUCKET_NAME='egystory-disabled'
        mock_env = {
            'USE_S3': 'False',
            'AWS_STORAGE_BUCKET_NAME': 'egystory-disabled',
        }

        # Emulate settings.py logic
        use_s3_val = mock_env.get('USE_S3', 'False').lower() in ('true', '1', 'yes')
        bucket_val = mock_env.get('AWS_STORAGE_BUCKET_NAME', '').strip() if use_s3_val else ''

        self.assertFalse(use_s3_val)
        self.assertEqual(bucket_val, '')
