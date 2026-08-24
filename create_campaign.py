import os
import sys
# pyrefly: ignore [missing-import]
import django
from decimal import Decimal
from datetime import timedelta
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
from django.core.files import File

# Add current directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egystory.settings')
django.setup()

from campaigns.models import Campaign, CaseType, CampaignStatus
from accounts.models import User

# Get first user as owner
owner = User.objects.first()

title = "عمر ويونس — طفلان مصريان مصابان بضمور العضلات دوشين"
story = "عمر ويونس — طفلان مصريان مصابان بضمور العضلات دوشين. ووافقت وزارة التضامن في أغسطس 2026 على فتح حساب لجمع التبرعات لعلاجهما، وتبلغ تكلفة العلاج المذكورة للحالة حوالي 300 مليون جنيه."
target_amount = Decimal('300000000.00')
deadline = timezone.now().date() + timedelta(days=365)

from django.conf import settings

# Image path
image_path = os.path.join(settings.MEDIA_ROOT, 'campaigns', '268.webp')
# Document path
doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blank_placeholder.txt")

campaign = Campaign(
    owner=owner,
    title=title,
    story=story,
    target_amount=target_amount,
    case_type=CaseType.RARE,
    status=CampaignStatus.PENDING,
    deadline=deadline,
    initial_raised_amount=Decimal('0.00'),
)

with open(image_path, 'rb') as img_f:
    campaign.campaign_image.save('omar_younes.png', File(img_f), save=False)
    
with open(doc_path, 'rb') as doc_f:
    campaign.supporting_document.save('blank_placeholder.txt', File(doc_f), save=False)

campaign.save()
print("Campaign created successfully!")
