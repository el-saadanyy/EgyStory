from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, F, Count
from django.http import JsonResponse
from django.urls import reverse
from .models import (
    Campaign, CampaignStatus, CaseType, Category, Tag, 
    CampaignImage, CampaignRating, CampaignReport, Comment, CommentReport
)
from .forms import (
    CampaignForm, DonationForm, RatingForm, ReportForm, 
    CommentForm, CommentReportForm
)

def campaign_autocomplete(request):
    """
    Lightweight JSON endpoint for campaign search autocomplete suggestions.
    Searches by title or tag name for active/completed campaigns.
    """
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})

    base_qs = Campaign.objects.filter(
        status__in=[CampaignStatus.ACTIVE, CampaignStatus.COMPLETED]
    )

    title_matches = base_qs.filter(title__icontains=query).distinct()[:6]
    suggestions = []
    seen_ids = set()

    for c in title_matches:
        seen_ids.add(c.id)
        suggestions.append({
            'id': c.id,
            'title': c.title,
            'url': reverse('campaigns:case_detail', kwargs={'campaign_id': c.id}),
            'match_type': 'Campaign'
        })

    if len(suggestions) < 6:
        tag_matches = (
            base_qs.filter(tags__name__icontains=query)
            .exclude(id__in=seen_ids)
            .prefetch_related('tags')
            .distinct()[:6 - len(suggestions)]
        )
        for c in tag_matches:
            matching_tag = next((t for t in c.tags.all() if query.lower() in t.name.lower()), None)
            tag_label = f"Tag: {matching_tag.name}" if matching_tag else "Tag match"
            suggestions.append({
                'id': c.id,
                'title': c.title,
                'url': reverse('campaigns:case_detail', kwargs={'campaign_id': c.id}),
                'match_type': tag_label
            })

    return JsonResponse({'suggestions': suggestions})


def case_list(request):
    campaigns = Campaign.objects.filter(
        status__in=[CampaignStatus.ACTIVE, CampaignStatus.COMPLETED]
    ).select_related('category', 'owner').prefetch_related('tags')
    
    query = request.GET.get('q')
    if query:
        campaigns = campaigns.filter(
            Q(title__icontains=query) | Q(story__icontains=query) | Q(tags__name__icontains=query)
        ).distinct()

    selected_category = request.GET.get('category')
    if selected_category:
        if selected_category.isdigit():
            campaigns = campaigns.filter(Q(category__slug=selected_category) | Q(category__id=int(selected_category)))
        else:
            campaigns = campaigns.filter(category__slug=selected_category)

    selected_tag = request.GET.get('tag')
    if selected_tag:
        if selected_tag.isdigit():
            campaigns = campaigns.filter(Q(tags__slug=selected_tag) | Q(tags__id=int(selected_tag))).distinct()
        else:
            campaigns = campaigns.filter(tags__slug=selected_tag).distinct()

    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'rare':
        campaigns = campaigns.filter(case_type=CaseType.RARE)
    elif filter_type == 'active':
        campaigns = campaigns.filter(status=CampaignStatus.ACTIVE)
    elif filter_type == 'completed':
        campaigns = campaigns.filter(status=CampaignStatus.COMPLETED)
    elif filter_type == 'almost_funded':
        campaigns = [
            c for c in campaigns 
            if c.status == CampaignStatus.ACTIVE 
            and 80 <= c.get_progress_percentage() < 100 
            and c.get_total_raised() < c.target_amount
        ]
    elif filter_type == 'critical':
        campaigns = [c for c in campaigns if hasattr(c, 'is_critical') and c.is_critical() and c.status == CampaignStatus.ACTIVE]

    if not isinstance(campaigns, list):
        campaigns = list(campaigns)

    sort_type = request.GET.get('sort', 'newest')
    if sort_type == 'most_urgent':
        campaigns.sort(key=lambda c: c.get_urgency_score(), reverse=True)
    elif sort_type == 'almost_funded':
        campaigns.sort(key=lambda c: c.get_progress_percentage(), reverse=True)
    elif sort_type == 'recently_completed':
        completed = [c for c in campaigns if c.status == CampaignStatus.COMPLETED]
        completed.sort(key=lambda c: c.updated_at, reverse=True)
        others = [c for c in campaigns if c.status != CampaignStatus.COMPLETED]
        campaigns = completed + others
    else:
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


def get_similar_campaigns(campaign):
    """
    Retrieves up to 4 similar active campaigns scored by matching category and shared tags.
    Optimized to eliminate N+1 queries by evaluating preloaded tag sets in memory.
    """
    if not campaign:
        return []

    category_id = campaign.category_id
    tag_ids = set(campaign.tags.values_list('id', flat=True))

    if not category_id and not tag_ids:
        return []

    candidates = (
        Campaign.objects.filter(status=CampaignStatus.ACTIVE)
        .exclude(id=campaign.id)
        .select_related('category', 'owner')
        .prefetch_related('tags')
    )

    scored_candidates = []
    for c in candidates:
        score = 0
        if category_id and c.category_id == category_id:
            score += 10
        
        if tag_ids:
            c_tag_ids = {tag.id for tag in c.tags.all()}
            matching_tags = len(c_tag_ids.intersection(tag_ids))
            score += (matching_tags * 5)

        if score > 0:
            scored_candidates.append((score, c.created_at, c))

    scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored_candidates[:4]]


def case_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if campaign.status not in [CampaignStatus.ACTIVE, CampaignStatus.COMPLETED] and request.user != campaign.owner and not request.user.is_staff:
        messages.error(request, 'This campaign is not available.')
        return redirect('campaigns:case_list')
    
    user_rating = None
    user_report = None
    if request.user.is_authenticated:
        user_rating = CampaignRating.objects.filter(campaign=campaign, user=request.user).first()
        user_report = CampaignReport.objects.filter(campaign=campaign, reporter=request.user).first()

    rating_data = campaign.get_star_rating_data()
    report_form = ReportForm()
    comment_form = CommentForm()
    can_creator_cancel = campaign.can_creator_cancel(request.user)
    similar_campaigns = get_similar_campaigns(campaign)
    
    comments = campaign.comments.filter(parent__isnull=True).select_related('user').prefetch_related('replies__user').order_by('-created_at') if hasattr(campaign, 'comments') else []

    return render(request, 'campaigns/case_detail.html', {
        'campaign': campaign,
        'user_rating': user_rating,
        'user_report': user_report,
        'rating_data': rating_data,
        'report_form': report_form,
        'comment_form': comment_form,
        'comments': comments,
        'can_creator_cancel': can_creator_cancel,
        'similar_campaigns': similar_campaigns,
    })


@login_required
def add_comment(request, campaign_id, parent_id=None):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        req_parent_id = parent_id or request.POST.get('parent_id')
        parent_comment = None

        if req_parent_id:
            try:
                parent_comment = Comment.objects.get(id=req_parent_id)
                # Verify that parent belongs to the same campaign
                if parent_comment.campaign_id != campaign.id:
                    messages.error(request, 'Cannot reply to a comment from a different campaign.')
                    return redirect('campaigns:case_detail', campaign_id=campaign.id)
            except (Comment.DoesNotExist, ValueError):
                messages.error(request, 'The comment you are replying to does not exist.')
                return redirect('campaigns:case_detail', campaign_id=campaign.id)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.campaign = campaign
            comment.user = request.user
            comment.parent = parent_comment
            comment.save()
            if parent_comment:
                messages.success(request, 'Your reply has been posted successfully.')
            else:
                messages.success(request, 'Your comment has been added successfully.')
        else:
            messages.error(request, 'Failed to post comment. Please check your text.')
    return redirect('campaigns:case_detail', campaign_id=campaign.id)


@login_required
def report_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    campaign_id = comment.campaign.id
    if request.method == 'POST':
        form = CommentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.comment = comment
            report.reporter = request.user
            report.save()
            messages.success(request, 'Thank you. The comment has been reported for review.')
        else:
            messages.error(request, 'Failed to submit report.')
    return redirect('campaigns:case_detail', campaign_id=campaign_id)


@login_required
def rate_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if request.method != 'POST':
        return redirect('campaigns:case_detail', campaign_id=campaign.id)

    form = RatingForm(request.POST)
    if form.is_valid():
        score = form.cleaned_data['score']
        rating, created = CampaignRating.objects.update_or_create(
            campaign=campaign,
            user=request.user,
            defaults={'score': score}
        )
        if created:
            messages.success(request, 'Thank you! Your rating has been submitted.')
        else:
            messages.success(request, 'Your rating has been updated.')
    else:
        messages.error(request, 'Invalid rating score submitted.')

    return redirect('campaigns:case_detail', campaign_id=campaign.id)


@login_required
def report_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.campaign = campaign
            report.reporter = request.user
            report.save()
            messages.success(request, 'Thank you. Your report has been submitted for review by our moderation team.')
        else:
            messages.error(request, 'Failed to submit report. Please check the details provided.')
    return redirect('campaigns:case_detail', campaign_id=campaign.id)


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
    active_campaigns = Campaign.objects.filter(status=CampaignStatus.ACTIVE).order_by('-created_at')
    
    if request.method == 'POST':
        campaign_id = request.POST.get('campaign_id')
        if campaign_id:
            return redirect('campaigns:donate', campaign_id=campaign_id)
        else:
            messages.error(request, 'Please select a campaign.')
            
    return render(request, 'campaigns/donate_general.html', {
        'active_campaigns': active_campaigns,
    })


@login_required
def cancel_campaign(request, campaign_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('campaigns:case_detail', campaign_id=campaign_id)

    campaign = get_object_or_404(Campaign, id=campaign_id)

    if campaign.owner != request.user:
        messages.error(request, 'You do not have permission to cancel this campaign.')
        return redirect('campaigns:case_detail', campaign_id=campaign_id)

    if not campaign.can_creator_cancel(request.user):
        messages.error(request, 'Campaign cannot be cancelled because raised amount has reached or exceeded 25% of the target goal.')
        return redirect('campaigns:case_detail', campaign_id=campaign_id)

    campaign.status = CampaignStatus.CANCELLED
    campaign.save(update_fields=['status'])

    messages.success(request, f'Campaign "{campaign.title}" has been successfully cancelled.')
    return redirect('campaigns:case_detail', campaign_id=campaign_id)