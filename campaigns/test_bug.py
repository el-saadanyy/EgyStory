from django.test import TestCase
from decimal import Decimal
from accounts.models import User
from campaigns.models import Campaign, CampaignStatus, CaseType
from campaigns.forms import CampaignForm
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from PIL import Image
import datetime

class CampaignCreationBugTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='bugtest@egystory.com',
            password='pwd',
            first_name='Test',
            last_name='User'
        )
        
        # Create a valid tiny image using Pillow
        file_obj = io.BytesIO()
        image = Image.new('RGB', (10, 10), color='white')
        image.save(file_obj, 'JPEG')
        file_obj.seek(0)
        self.img = SimpleUploadedFile(name='test_image.jpg', content=file_obj.read(), content_type='image/jpeg')

    def test_normal_campaign_empty_initial_raised_amount(self):
        data = {
            'title': 'Test Normal',
            'story': 'Testing normal campaign empty initial',
            'target_amount': '5000',
            'initial_raised_amount': '',
            'case_type': CaseType.NORMAL,
            'deadline': '',
            'supporting_document': ''
        }
        form = CampaignForm(data=data, files={'campaign_image': self.img})
        self.assertTrue(form.is_valid(), form.errors)

    def test_normal_campaign_zero_initial_raised_amount(self):
        data = {
            'title': 'Test Normal Zero',
            'story': 'Testing normal campaign zero initial',
            'target_amount': '5000',
            'initial_raised_amount': '0',
            'case_type': CaseType.NORMAL,
            'deadline': '',
            'supporting_document': ''
        }
        # recreate image because file pointer might be at EOF
        file_obj = io.BytesIO()
        image = Image.new('RGB', (10, 10), color='white')
        image.save(file_obj, 'JPEG')
        file_obj.seek(0)
        img = SimpleUploadedFile(name='test_image.jpg', content=file_obj.read(), content_type='image/jpeg')
        form = CampaignForm(data=data, files={'campaign_image': img})
        self.assertTrue(form.is_valid(), form.errors)

    def test_normal_campaign_positive_initial_raised_amount(self):
        data = {
            'title': 'Test Normal Pos',
            'story': 'Testing normal campaign positive initial',
            'target_amount': '5000',
            'initial_raised_amount': '100',
            'case_type': CaseType.NORMAL,
            'deadline': '',
            'supporting_document': ''
        }
        file_obj = io.BytesIO()
        image = Image.new('RGB', (10, 10), color='white')
        image.save(file_obj, 'JPEG')
        file_obj.seek(0)
        img = SimpleUploadedFile(name='test_image.jpg', content=file_obj.read(), content_type='image/jpeg')
        form = CampaignForm(data=data, files={'campaign_image': img})
        self.assertTrue(form.is_valid(), form.errors)

    def test_rare_campaign_missing_deadline_fails(self):
        data = {
            'title': 'Test Rare Missing',
            'story': 'Testing rare campaign missing deadline',
            'target_amount': '5000',
            'initial_raised_amount': '0',
            'case_type': CaseType.RARE,
            'deadline': '',
            'supporting_document': ''
        }
        file_obj = io.BytesIO()
        image = Image.new('RGB', (10, 10), color='white')
        image.save(file_obj, 'JPEG')
        file_obj.seek(0)
        img = SimpleUploadedFile(name='test_image.jpg', content=file_obj.read(), content_type='image/jpeg')
        # supporting_document does not need to be an image
        doc = SimpleUploadedFile(name='test_doc.pdf', content=b'fake_doc', content_type='application/pdf')
        form = CampaignForm(data=data, files={'campaign_image': img, 'supporting_document': doc})
        self.assertFalse(form.is_valid())
        self.assertIn('deadline', form.errors)

    def test_rare_campaign_missing_doc_fails(self):
        data = {
            'title': 'Test Rare Missing',
            'story': 'Testing rare campaign missing doc',
            'target_amount': '5000',
            'initial_raised_amount': '0',
            'case_type': CaseType.RARE,
            'deadline': '2027-01-01',
            'supporting_document': ''
        }
        file_obj = io.BytesIO()
        image = Image.new('RGB', (10, 10), color='white')
        image.save(file_obj, 'JPEG')
        file_obj.seek(0)
        img = SimpleUploadedFile(name='test_image.jpg', content=file_obj.read(), content_type='image/jpeg')
        form = CampaignForm(data=data, files={'campaign_image': img})
        self.assertFalse(form.is_valid())
        self.assertIn('supporting_document', form.errors)
        
    def test_amount_raised_exceeds_target_fails(self):
        data = {
            'title': 'Test Exceed',
            'story': 'Testing exceed target',
            'target_amount': '5000',
            'initial_raised_amount': '6000',
            'case_type': CaseType.NORMAL,
            'deadline': '',
            'supporting_document': ''
        }
        file_obj = io.BytesIO()
        image = Image.new('RGB', (10, 10), color='white')
        image.save(file_obj, 'JPEG')
        file_obj.seek(0)
        img = SimpleUploadedFile(name='test_image.jpg', content=file_obj.read(), content_type='image/jpeg')
        form = CampaignForm(data=data, files={'campaign_image': img})
        self.assertFalse(form.is_valid())
        self.assertIn('initial_raised_amount', form.errors)
