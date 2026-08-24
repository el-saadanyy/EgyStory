import os
import sys
import django
from django.core.files import File

# Add current directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egystory.settings')
django.setup()

from django.conf import settings

title = "عمر ويونس — طفلان مصريان مصابان بضمور العضلات دوشين"
new_image_path = os.path.join(settings.MEDIA_ROOT, 'campaigns', '268.webp')

try:
    campaign = Campaign.objects.get(title=title)
    with open(new_image_path, 'rb') as img_f:
        campaign.campaign_image.save('268.webp', File(img_f), save=True)
    print("Campaign image updated successfully!")
except Campaign.DoesNotExist:
    print("Campaign not found.")
except Exception as e:
    print(f"Error: {e}")
