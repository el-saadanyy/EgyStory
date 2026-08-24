import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egystory.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.test.client import Client
from accounts.models import User
from campaigns.models import CaseType
from django.core.files.uploadedfile import SimpleUploadedFile

c = Client()
user = User.objects.first()
c.force_login(user)

img_path = os.path.join(settings.MEDIA_ROOT, 'campaigns', '268.webp')
with open(img_path, "rb") as f:
    img = SimpleUploadedFile(name='test_image.webp', content=f.read(), content_type='image/webp')

data = {
    'title': 'Test View Normal Campaign',
    'story': 'Testing via view to see if it fails.',
    'target_amount': '5000',
    'initial_raised_amount': '',
    'case_type': CaseType.NORMAL,
    'campaign_image': img
}

response = c.post('/cases/new/', data)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    # Form failed validation
    form = response.context['form']
    print("Form Errors:", form.errors)
