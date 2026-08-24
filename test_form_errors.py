import os, sys, django
sys.path.append(os.path.dirname(os.path.abspath('manage.py')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egystory.settings')
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')
from django.test import Client
from accounts.models import User
user = User.objects.filter(email__startswith='shiref').first()
if not user:
    print('User not found')
    sys.exit(1)
c = Client(SERVER_NAME='localhost')
c.force_login(user)

image_path = 'test_image.jpg'
with open(image_path, 'rb') as f:
    response = c.post('/cases/new/', {
        'title': 'Test Title',
        'story': 'Test Story that is long enough to be valid',
        'target_amount': '1000.00',
        'initial_raised_amount': '',
        'case_type': 'Normal',
        'deadline': '',
        'campaign_image': f,
    })
print('Status:', response.status_code)
if response.status_code == 200:
    if not response.context:
        import re
        errors = re.findall(r'color: var\(--color-danger\).*?>(.*?)</div>', response.content.decode('utf-8'))
        print(errors)
elif response.status_code == 302:
    print('Redirected to:', response.url)
