import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egystory.settings')
django.setup()

from campaigns.forms import CampaignForm
from campaigns.models import CaseType
from django.core.files.uploadedfile import SimpleUploadedFile

from django.conf import settings

img_path = os.path.join(settings.MEDIA_ROOT, 'campaigns', '268.webp')
with open(img_path, "rb") as f:
    img = SimpleUploadedFile(name='test_image.webp', content=f.read(), content_type='image/webp')

data = {
    'title': 'Test Normal Campaign',
    'story': 'This is a story that goes on for a bit.',
    'target_amount': '5000',
    'initial_raised_amount': '',
    'case_type': CaseType.NORMAL
}

files = {'campaign_image': img}

form = CampaignForm(data=data, files=files)
if not form.is_valid():
    print("Form is invalid!")
    print(form.errors)
else:
    print("Form is valid!")
    print(form.cleaned_data)
