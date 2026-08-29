from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.models import User
from .decorators import admin_required, superuser_required


def admin_login(request):
    """Separate admin login page."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').lower().strip()
        password = request.POST.get('password', '')

        try:
            user_obj = User.objects.get(email=email)
            if not user_obj.is_active:
                messages.error(request, 'This account is not activated.')
                return render(request, 'administration/login.html')
            if not user_obj.is_staff:
                messages.error(request, 'You do not have admin access.')
                return render(request, 'administration/login.html')
        except User.DoesNotExist:
            messages.error(request, 'Invalid credentials.')
            return render(request, 'administration/login.html')

        user = authenticate(request, username=email, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, 'Welcome back! You have been logged in successfully.')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'administration/login.html')


def admin_logout(request):
    if request.method == 'POST':
        logout(request)
    return redirect('admin_login')


@admin_required
def dashboard(request):
    """
    EgyStory Admin Dashboard — Phase 2.
    """
    from accounts.models import User
    from campaigns.models import Campaign, CampaignStatus, Donation, Tag
    from django.db.models import Sum
    
    stats = {
        'total_users': User.objects.filter(is_staff=False).count(),
        'active_users': User.objects.filter(is_active=True, is_staff=False).count(),
        'pending_users': User.objects.filter(is_active=False, is_staff=False).count(),
        'total_campaigns': Campaign.objects.count(),
        'pending_campaigns': Campaign.objects.filter(status=CampaignStatus.PENDING).count(),
        'active_campaigns': Campaign.objects.filter(status=CampaignStatus.ACTIVE).count(),
        'completed_campaigns': Campaign.objects.filter(status=CampaignStatus.COMPLETED).count(),
        'expired_campaigns': Campaign.objects.filter(status=CampaignStatus.EXPIRED).count(),
        'total_donations': Donation.objects.count(),
        'total_raised': Donation.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_tags': Tag.objects.count(),
    }
    
    pending_campaigns = Campaign.objects.filter(status=CampaignStatus.PENDING).order_by('created_at')
    active_campaigns = Campaign.objects.filter(status=CampaignStatus.ACTIVE).order_by('-created_at')
    completed_campaigns = Campaign.objects.filter(status=CampaignStatus.COMPLETED).select_related('owner', 'category').order_by('-updated_at')
    
    return render(request, 'administration/dashboard.html', {
        'stats': stats,
        'pending_campaigns': pending_campaigns,
        'active_campaigns': active_campaigns,
        'completed_campaigns': completed_campaigns,
    })

@admin_required
def delete_completed_campaign(request, campaign_id):
    """
    Safely delete a Completed campaign by an authorized Staff / Admin user.
    Strictly verifies that the campaign status is 'Completed'.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method for deletion.')
        return redirect('admin_dashboard')

    from campaigns.models import Campaign, CampaignStatus
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if campaign.status != CampaignStatus.COMPLETED:
        messages.error(request, f'Cannot delete campaign "{campaign.title}" because it is not completed.')
        return redirect('admin_dashboard')

    campaign_title = campaign.title
    campaign.delete()
    messages.success(request, f'Completed campaign "{campaign_title}" has been permanently deleted.')
    return redirect('admin_dashboard')

@admin_required
def campaign_moderation(request):
    """
    Dedicated Campaign Moderation Page: Review and approve/reject pending campaigns.
    """
    from campaigns.models import Campaign, CampaignStatus
    pending_campaigns = Campaign.objects.filter(status=CampaignStatus.PENDING).order_by('created_at')
    
    return render(request, 'administration/moderation.html', {
        'pending_campaigns': pending_campaigns,
    })

@admin_required
def campaign_action(request, campaign_id, action):
    from campaigns.models import Campaign, CampaignStatus
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if action == 'approve':
        campaign.status = CampaignStatus.ACTIVE
        campaign.save(update_fields=['status'])
        messages.success(request, f'Campaign "{campaign.title}" approved and is now Active.')
    
    elif action == 'reject':
        campaign.status = CampaignStatus.CANCELLED
        campaign.save(update_fields=['status'])
        messages.success(request, f'Campaign "{campaign.title}" rejected.')
        
    elif action == 'cancel':
        campaign.status = CampaignStatus.CANCELLED
        campaign.save(update_fields=['status'])
        messages.success(request, f'Campaign "{campaign.title}" cancelled.')
        
    return redirect('admin_dashboard')

@superuser_required
def toggle_manual_critical(request, campaign_id):
    """Toggle manual Critical classification override for a campaign (Superuser only)."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_dashboard')
        
    from campaigns.models import Campaign
    campaign = get_object_or_404(Campaign, id=campaign_id)
    campaign.is_manual_critical = not campaign.is_manual_critical
    campaign.save(update_fields=['is_manual_critical'])
    
    if campaign.is_manual_critical:
        messages.success(request, f'Campaign "{campaign.title}" manually set to Critical.')
    else:
        messages.success(request, f'Manual Critical override removed for "{campaign.title}".')
        
    return redirect('admin_dashboard')

@admin_required
def toggle_featured(request, campaign_id):
    """Toggle Featured status for a campaign (Staff / Admin)."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_dashboard')
        
    from campaigns.models import Campaign
    campaign = get_object_or_404(Campaign, id=campaign_id)
    campaign.is_featured = not campaign.is_featured
    campaign.save(update_fields=['is_featured'])
    
    if campaign.is_featured:
        messages.success(request, f'Campaign "{campaign.title}" is now marked as Featured.')
    else:
        messages.success(request, f'Featured status removed from "{campaign.title}".')
        
    return redirect('admin_dashboard')

@admin_required
def user_management(request):
    """
    List all normal users (non-staff) for the administration.
    """
    from accounts.models import User
    
    # Exclude staff and order by newest first
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    
    return render(request, 'administration/users.html', {
        'users': users,
    })

@admin_required
def delete_user(request, user_id):
    """
    Delete a specific user by ID. Handles cascade deletion naturally.
    Requires POST. Protected against deleting staff, superusers, or the protected email.
    """
    from accounts.models import User
    
    if request.method != 'POST':
        messages.error(request, 'Invalid method for deletion.')
        return redirect('admin_users')
        
    user_to_delete = get_object_or_404(User, id=user_id)
    
    # Protection rules
    if user_to_delete.is_staff or user_to_delete.is_superuser:
        messages.error(request, 'Cannot delete staff or superuser accounts.')
        return redirect('admin_users')
        
    # Prevent self-deletion just in case
    if user_to_delete == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('admin_users')
        
    # Perform deletion
    user_to_delete.delete()
    messages.success(request, f'User {user_to_delete.get_full_name()} (and their related data) has been successfully deleted.')
    
    return redirect('admin_users')

# ── Admin Management (Superuser Only) ──────────────────────────────────────

from .decorators import superuser_required
from .forms import AdminUserForm, AdminPasswordResetForm

@superuser_required
def admin_management(request):
    """
    List all staff users (admin) for superuser.
    """
    from accounts.models import User
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    return render(request, 'administration/admins.html', {
        'admins': admins,
    })

@superuser_required
def admin_create(request):
    """Create a new staff user."""
    if request.method == 'POST':
        form = AdminUserForm(request.POST, is_creation=True)
        if form.is_valid():
            form.save()
            messages.success(request, 'New Admin created successfully.')
            return redirect('admin_management')
    else:
        form = AdminUserForm(is_creation=True)
        
    return render(request, 'administration/admin_form.html', {
        'form': form,
        'title': 'Create Admin',
        'is_edit': False
    })

@superuser_required
def admin_edit(request, admin_id):
    """Edit an existing staff user."""
    from accounts.models import User
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True)
    
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=admin_obj, is_creation=False)
        if form.is_valid():
            # Prevent removing superuser from self
            if admin_obj == request.user and not form.cleaned_data.get('is_superuser'):
                messages.error(request, 'You cannot remove superuser privileges from yourself.')
            else:
                form.save()
                messages.success(request, 'Admin details updated successfully.')
                return redirect('admin_management')
    else:
        form = AdminUserForm(instance=admin_obj, is_creation=False)
        
    return render(request, 'administration/admin_form.html', {
        'form': form,
        'title': f'Edit Admin: {admin_obj.get_full_name()}',
        'is_edit': True,
        'admin_obj': admin_obj
    })

@superuser_required
def admin_toggle_status(request, admin_id):
    """Toggle is_active for an admin."""
    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('admin_management')
        
    from accounts.models import User
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True)
    
    if admin_obj == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('admin_management')
        
    admin_obj.is_active = not admin_obj.is_active
    admin_obj.save(update_fields=['is_active'])
    status_str = "activated" if admin_obj.is_active else "deactivated"
    messages.success(request, f'Admin account {status_str} successfully.')
    return redirect('admin_management')

@superuser_required
def admin_reset_password(request, admin_id):
    """Reset an admin's password."""
    from accounts.models import User
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True)
    
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            admin_obj.set_password(form.cleaned_data['new_password'])
            admin_obj.save(update_fields=['password'])
            messages.success(request, 'Admin password has been reset successfully.')
            return redirect('admin_management')
    else:
        form = AdminPasswordResetForm()
        
    return render(request, 'administration/admin_password_reset.html', {
        'form': form,
        'admin_obj': admin_obj
    })

@superuser_required
def admin_delete(request, admin_id):
    """Delete an admin account."""
    if request.method != 'POST':
        messages.error(request, 'Invalid method.')
        return redirect('admin_management')
        
    from accounts.models import User
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True)
    
    if admin_obj == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('admin_management')
        
    admin_obj.delete()
    messages.success(request, 'Admin account has been permanently deleted.')
    return redirect('admin_management')


# ── Tag Management (Staff / Admin) ──────────────────────────────────────

@admin_required
def tag_management(request):
    """
    List and create Tags in custom Admin Dashboard.
    """
    from campaigns.models import Tag
    from django.db.models import Count

    if request.method == 'POST':
        tag_name = request.POST.get('name', '').strip()
        if tag_name:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            if created:
                messages.success(request, f'Tag "{tag.name}" created successfully.')
            else:
                messages.warning(request, f'Tag "{tag.name}" already exists.')
        else:
            messages.error(request, 'Tag name cannot be empty.')
        return redirect('admin_tags')

    tags = Tag.objects.annotate(campaign_count=Count('campaigns')).order_by('name')
    return render(request, 'administration/tags.html', {
        'tags': tags,
    })

@admin_required
def delete_tag(request, tag_id):
    """
    Delete a specific Tag by ID. Requires POST.
    """
    from campaigns.models import Tag

    if request.method != 'POST':
        messages.error(request, 'Invalid method for deletion.')
        return redirect('admin_tags')

    tag = get_object_or_404(Tag, id=tag_id)
    tag_name = tag.name
    tag.delete()
    messages.success(request, f'Tag "{tag_name}" has been successfully deleted.')

    return redirect('admin_tags')

@admin_required
def edit_tag(request, tag_id):
    """
    Edit an existing Tag name in custom Admin Dashboard.
    """
    from campaigns.models import Tag
    tag = get_object_or_404(Tag, id=tag_id)

    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if new_name:
            tag.name = new_name
            from django.utils.text import slugify
            tag.slug = slugify(new_name)
            tag.save()
            messages.success(request, f'Tag updated to "{tag.name}".')
            return redirect('admin_tags')
        else:
            messages.error(request, 'Tag name cannot be empty.')

    return render(request, 'administration/tag_form.html', {
        'tag': tag,
    })

@admin_required
def admin_campaign_edit(request, campaign_id):
    """
    Edit Campaign details and assign Multiple Tags in custom Admin Dashboard.
    """
    from campaigns.models import Campaign, Tag, Category, CaseType, CampaignStatus
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        story = request.POST.get('story', '').strip()
        category_id = request.POST.get('category')
        case_type = request.POST.get('case_type')
        status = request.POST.get('status')
        selected_tag_ids = request.POST.getlist('tags')

        if title:
            campaign.title = title
        if story:
            campaign.story = story
        if category_id:
            campaign.category_id = category_id
        else:
            campaign.category = None
        if case_type:
            campaign.case_type = case_type
        if status:
            campaign.status = status

        campaign.is_featured = request.POST.get('is_featured') in ['on', 'true', '1', True]

        campaign.save()
        campaign.tags.set(selected_tag_ids)

        messages.success(request, f'Campaign "{campaign.title}" updated successfully with {len(selected_tag_ids)} tag(s).')
        return redirect('admin_dashboard')

    categories = Category.objects.all()
    all_tags = Tag.objects.all()
    campaign_tag_ids = set(campaign.tags.values_list('id', flat=True))

    return render(request, 'administration/campaign_edit.html', {
        'campaign': campaign,
        'categories': categories,
        'all_tags': all_tags,
        'campaign_tag_ids': campaign_tag_ids,
        'case_types': CaseType.choices,
        'status_choices': CampaignStatus.choices,
    })

@admin_required
def admin_reports(request):
    """
    Moderation Panel: Manage reported campaigns in custom Admin Dashboard.
    """
    from campaigns.models import CampaignReport, ReportStatus
    
    current_status = request.GET.get('status', 'all')
    reports = CampaignReport.objects.select_related('campaign', 'reporter').all()
    
    if current_status == 'pending':
        reports = reports.filter(status=ReportStatus.PENDING)
    elif current_status == 'reviewed':
        reports = reports.filter(status=ReportStatus.REVIEWED)
    elif current_status == 'dismissed':
        reports = reports.filter(status=ReportStatus.DISMISSED)
    elif current_status == 'action_taken':
        reports = reports.filter(status=ReportStatus.ACTION_TAKEN)

    return render(request, 'administration/reports.html', {
        'reports': reports,
        'current_status': current_status,
        'status_choices': ReportStatus.choices,
    })

@admin_required
def admin_report_action(request, report_id, action):
    """
    Take action on a reported campaign (Dismiss, Mark Reviewed, or Cancel Campaign).
    """
    from campaigns.models import CampaignReport, ReportStatus, CampaignStatus
    report = get_object_or_404(CampaignReport, id=report_id)
    
    if action == 'dismiss':
        report.status = ReportStatus.DISMISSED
        report.save(update_fields=['status'])
        messages.success(request, f'Report #{report.id} dismissed.')
    elif action == 'mark_reviewed':
        report.status = ReportStatus.REVIEWED
        report.save(update_fields=['status'])
        messages.success(request, f'Report #{report.id} marked as Reviewed.')
    elif action == 'cancel_campaign':
        report.status = ReportStatus.ACTION_TAKEN
        report.save(update_fields=['status'])
        campaign = report.campaign
        campaign.status = CampaignStatus.CANCELLED
        campaign.save(update_fields=['status'])
        messages.warning(request, f'Campaign "{campaign.title}" has been cancelled due to report #{report.id}.')

    return redirect('admin_reports')


@admin_required
def admin_comments(request):
    """
    Comment Moderation Page — lists all top-level comments and replies
    so an authorized admin can review and delete inappropriate content.
    """
    from campaigns.models import Comment
    comments = Comment.objects.select_related('user', 'campaign', 'parent').order_by('-created_at')
    return render(request, 'administration/comments.html', {
        'comments': comments,
    })


@admin_required
def delete_comment(request, comment_id):
    """
    Permanently delete a comment (and its replies, via CASCADE).
    Strictly POST-only and CSRF-protected.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method for deletion.')
        return redirect('admin_comments')

    from campaigns.models import Comment
    comment = get_object_or_404(Comment, id=comment_id)
    campaign_id = comment.campaign_id
    reply_count = comment.replies.count()

    comment.delete()

    if reply_count:
        messages.success(
            request,
            f'Comment #{comment_id} and its {reply_count} reply(ies) have been permanently deleted.'
        )
    else:
        messages.success(request, f'Comment #{comment_id} has been permanently deleted.')

    return redirect('admin_comments')




