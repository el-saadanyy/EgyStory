import os
import sys
import django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egystory.settings')
django.setup()
from campaigns.models import Campaign
for c in Campaign.objects.all():
    print(c.id, c.status, c.case_type)
