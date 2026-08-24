from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, F
from .models import Campaign, CampaignStatus, CaseType, Category, Tag, CampaignImage
from .forms import CampaignForm, DonationForm

def case_list(request):
    # Only show Active or Completed publicly
    campaigns = Campaign.objects.filter(status__in=[CampaignStatus.ACTIVE, CampaignStatus.COMPLETED])
    
    # Search by title, story, or tag name
    query = request.GET.get('q')
    if query:
        campaigns = campaigns.filter(
            Q(title__icontains=query) | Q(story__icontains=query) | Q(tags__name__icontains=query)
        ).distinct()

    # Category Filter
    selected_category = request.GET.get('category')
    if selected_category:
        campaigns = campaigns.filter(Q(category__slug=selected_category) | Q(category__id=selected_category) if selected_category.isdigit() else Q(category__slug=selected_category))

    # Tag Filter
    selected_tag = request.GET.get('tag')
    if selected_tag:
        campaigns = campaigns.filter(
            Q(tags__slug=selected_tag) | Q(tags__id=selected_tag) if selected_tag.isdigit() else Q(tags__slug=selected_tag)
        ).distinct()

    # Filter
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'rare':
        campaigns = campaigns.filter(case_type=CaseType.RARE)
    elif filter_type == 'active':
        campaigns = campaigns.filter(status=CampaignStatus.ACTIVE)
    elif filter_type == 'completed':
        campaigns = campaigns.filter(status=CampaignStatus.COMPLETED)
    elif filter_type == 'critical':
        # Critical is dynamic based on urgency score. We need to filter in python or build a complex DB query.
        # Since it's a simple project, we can filter in python.
        pass # Handle after DB query
    elif filter_type == 'almost_funded':
        # Let's say > 80%
        campaigns = [c for c in campaigns if c.get_progress_percentage() >= 80]

    # Evaluate QuerySet if not already a list
    if not isinstance(campaigns, list):
        campaigns = list(campaigns)

    if filter_type == 'critical':
        campaigns = [c for c in campaigns if c.is_critical() and c.status == CampaignStatus.ACTIVE]

    # Sort
    sort_type = request.GET.get('sort', 'newest')
    if sort_type == 'most_urgent':
        campaigns.sort(key=lambda c: c.get_urgency_score(), reverse=True)
    elif sort_type == 'almost_funded':
        campaigns.sort(key=lambda c: c.get_progress_percentage(), reverse=True)
    elif sort_type == 'recently_completed':
        # Sort by updated_at or created_at for completed
        completed = [c for c in campaigns if c.status == CampaignStatus.COMPLETED]
        completed.sort(key=lambda c: c.updated_at, reverse=True)
        others = [c for c in campaigns if c.status != CampaignStatus.COMPLETED]
        campaigns = completed + others
    else: # newest
        campaigns.sort(key=lambda c: c.created_at, reverse=True)

    categories = Category.objects.all()
    tags = Tag.objects.all()

    return render(request, 'campaigns/case_list.html', {
        'campaigns': campaigns,
        'categories': categories,
        'tags': tags,
        'selected_category': selected_category,
        'selected_tag': selected_tag,
        'current_filter': filter_type,
        'current_sort': sort_type,
        'query': query
    })

def case_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Don't show pending/cancelled to public unless owner
    if campaign.status not in [CampaignStatus.ACTIVE, CampaignStatus.COMPLETED] and request.user != campaign.owner and not request.user.is_staff:
        messages.error(request, 'This campaign is not available.')
        return redirect('campaigns:case_list')
    
    return render(request, 'campaigns/case_detail.html', {'campaign': campaign})

@login_required
def case_create(request):
    if not request.user.is_active:
        messages.error(request, 'You must activate your account before creating a campaign.')
        return redirect('profile')

    if request.method == 'POST':
        form = CampaignForm(request.POST, request.FILES)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.owner = request.user
            campaign.status = CampaignStatus.PENDING
            campaign.save()
            form.save_m2m()

            # Process multiple additional pictures
            additional_images = request.FILES.getlist('images')
            for img in additional_images:
                CampaignImage.objects.create(campaign=campaign, image=img)

            messages.success(request, 'Campaign created successfully and is pending review.')
            return redirect('profile')
    else:
        form = CampaignForm()
    
    return render(request, 'campaigns/case_form.html', {'form': form})

@login_required
def delete_campaign_image(request, image_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('campaigns:case_list')

    image_obj = get_object_or_404(CampaignImage, id=image_id)
    campaign = image_obj.campaign

    # Permission check: must be campaign owner or staff
    if request.user != campaign.owner and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to delete this image.")

    image_obj.delete()
    messages.success(request, 'Image removed successfully.')
    return redirect('campaigns:case_detail', campaign_id=campaign.id)


def donate(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if campaign.status != CampaignStatus.ACTIVE:
        messages.error(request, 'You can only donate to active campaigns.')
        return redirect('campaigns:case_detail', campaign_id=campaign.id)

    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.campaign = campaign
            donation.save()
            messages.success(request, 'Thank you for your donation!')
            return redirect('campaigns:case_detail', campaign_id=campaign.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {'donor_name': request.user.get_full_name(), 'donor_email': request.user.email}
        form = DonationForm(initial=initial)
    
    return render(request, 'campaigns/donate.html', {'form': form, 'campaign': campaign})

def donate_general(request):
    # This allows a user to select an active campaign before donating
    active_campaigns = Campaign.objects.filter(status=CampaignStatus.ACTIVE).order_by('-created_at')
    
    if request.method == 'POST':
        campaign_id = request.POST.get('campaign_id')
        if campaign_id:
            return redirect('campaigns:donate', campaign_id=campaign_id)
        else:
            messages.error(request, 'Please select a campaign.')
            
    return render(request, 'campaigns/donate_general.html', {'active_campaigns': active_campaigns})
