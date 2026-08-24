from django.shortcuts import render
from campaigns.models import Campaign, CampaignStatus, CaseType

def home(request):
    """EgyStory home page — Campaign Galleries."""
    active_campaigns = Campaign.objects.filter(status=CampaignStatus.ACTIVE)
    
    # Evaluate and score campaigns
    scored_campaigns = list(active_campaigns)
    
    # Separate Rare, Normal, and Critical
    rare_campaigns = [c for c in scored_campaigns if c.case_type == CaseType.RARE]
    rare_campaigns.sort(key=lambda c: c.get_urgency_score(), reverse=True)
    
    normal_campaigns = [c for c in scored_campaigns if c.case_type == CaseType.NORMAL]
    normal_campaigns.sort(key=lambda c: c.get_urgency_score(), reverse=True)
    
    critical_campaigns = [c for c in scored_campaigns if c.is_critical()]
    critical_campaigns.sort(key=lambda c: c.get_urgency_score(), reverse=True)

    # Main Slider (Max 5)
    # Priority: Up to 4 Critical, Up to 1 Rare
    slider_campaigns = []
    
    if rare_campaigns:
        slider_campaigns.append(rare_campaigns[0])
        # Up to 4 critical
        for c in critical_campaigns:
            if c not in slider_campaigns and len(slider_campaigns) < 5:
                slider_campaigns.append(c)
    else:
        # Up to 5 critical if no rare
        for c in critical_campaigns:
            if len(slider_campaigns) < 5:
                slider_campaigns.append(c)
                
    # If still less than 5, just fill with newest active campaigns
    if len(slider_campaigns) < 5:
        others = [c for c in scored_campaigns if c not in slider_campaigns]
        others.sort(key=lambda c: c.created_at, reverse=True)
        for c in others:
            if len(slider_campaigns) < 5:
                slider_campaigns.append(c)

    # Success Stories: Newest completed campaigns first (max 3)
    success_stories = Campaign.objects.filter(status=CampaignStatus.COMPLETED).order_by('-created_at')[:3]

    context = {
        'slider_campaigns': slider_campaigns,
        'critical_cases': critical_campaigns[:3],
        'rare_cases': rare_campaigns[:3],
        'normal_cases': normal_campaigns[:3],
        'success_stories': success_stories,
    }
    return render(request, 'home.html', context)
