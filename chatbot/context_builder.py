"""
Context Builder for EgyStory Chatbot Assistant.
Safely queries real database models without exposing raw database access to AI.
Provides strictly bounded, controlled context to prevent hallucinations.
"""

from decimal import Decimal
from django.db.models import Q
from campaigns.models import Campaign, CampaignStatus, Category, Tag

def get_platform_overview_context():
    """
    Returns general knowledge about EgyStory platform rules, features, and capabilities.
    """
    return (
        "EgyStory Platform Rules and Facts:\n"
        "- EgyStory is an Egyptian crowdfunding platform for community campaigns, medical aid, social cases, and emergencies.\n"
        "- Currency used: Egyptian Pounds (EGP).\n"
        "- Creating a Campaign: Registered users can click 'Start a Story' (/cases/new/). Required fields include title, category, story details, target goal amount, and primary cover image. Users can optionally upload gallery images and medical/verification supporting documents.\n"
        "- Campaign Statuses: 'Pending Review' (awaiting admin verification), 'Active' (publicly accepting donations), 'Completed' (target amount reached), 'Expired' (deadline passed), 'Cancelled'.\n"
        "- Donations: Users can donate directly to specific campaigns (/cases/<id>/donate/) or make general donations (/cases/donate/). The donation flow records donor name, email, amount in EGP, and an optional anonymous toggle.\n"
        "- User Accounts & Registration: Registration requires email, first name, last name, and Egyptian phone number. Email activation via OTP/token is required before first login.\n"
        "- User Profile & Account Management: Logged-in users can view their profile at /profile/ and edit personal details at /profile/edit/.\n"
        "- Account Deletion Procedure (How to delete an account): To delete an account, a logged-in user must:\n"
        "  1. Log in to their EgyStory account and navigate to their Profile page (/profile/).\n"
        "  2. Click on the 'Delete Account' link (or go directly to the confirmation page at /delete/).\n"
        "  3. On the Delete Account confirmation page, the user must enter their current account password (required for security verification) and check the confirmation box acknowledging that deletion is permanent and cannot be undone.\n"
        "  4. Click 'Yes, Delete My Account Permanently'. Upon successful confirmation, the account and associated profile data are permanently deleted, the user is logged out, and redirected to the home page.\n"
        "- Campaign Cancellation Rule: A campaign creator can only cancel their campaign if it is Pending or Active, AND the total amount raised is strictly LESS THAN 25% of the target goal.\n"
        "- Campaign Urgency & Critical Classification: Campaigns can be marked Critical manually by administrators or automatically when their urgency score reaches 70+ (based on deadline proximity, percentage remaining, and funding rate).\n"
    )

def search_relevant_campaigns(query_text, max_results=5):
    """
    Searches the live database for campaigns matching the user's query keywords.
    Returns a list of structured campaign summaries.
    """
    if not query_text or not query_text.strip():
        return []

    words = [w.strip() for w in query_text.split() if len(w.strip()) > 1]
    if not words:
        return []

    # Build Q filters across title, story, category name, and tags
    q_filter = Q()
    for word in words:
        q_filter |= (
            Q(title__icontains=word) |
            Q(story__icontains=word) |
            Q(category__name__icontains=word) |
            Q(tags__name__icontains=word)
        )

    # Only show active or completed campaigns to general users
    campaigns = (
        Campaign.objects.filter(status__in=[CampaignStatus.ACTIVE, CampaignStatus.COMPLETED])
        .filter(q_filter)
        .select_related('category', 'owner')
        .prefetch_related('tags')
        .distinct()[:max_results]
    )

    results = []
    for c in campaigns:
        tags_list = [t.name for t in c.tags.all()]
        results.append({
            'id': c.id,
            'title': c.title,
            'category': c.category.name if c.category else 'General',
            'case_type': c.case_type,
            'status': c.status,
            'target_amount': float(c.target_amount),
            'total_raised': float(c.get_total_raised()),
            'progress_percentage': c.get_progress_percentage(),
            'remaining_amount': float(c.get_remaining_amount()),
            'days_remaining': c.get_days_remaining(),
            'is_critical': c.is_critical(),
            'tags': tags_list,
            'story_summary': c.story[:200] + '...' if len(c.story) > 200 else c.story,
            'url': f"/cases/{c.id}/",
        })
    return results

def get_recommended_campaigns(limit=3):
    """
    Retrieves top active campaigns for recommendation (e.g. Critical, Rare, or urgent campaigns).
    """
    active_qs = (
        Campaign.objects.filter(status=CampaignStatus.ACTIVE)
        .select_related('category', 'owner')
        .prefetch_related('tags')
    )

    all_active = list(active_qs)
    if not all_active:
        return []

    # Sort primarily by urgency / critical status, and average rating
    all_active.sort(key=lambda c: (c.is_critical(), c.get_urgency_score(), c.get_average_rating()), reverse=True)
    top = all_active[:limit]

    results = []
    for c in top:
        tags_list = [t.name for t in c.tags.all()]
        results.append({
            'id': c.id,
            'title': c.title,
            'category': c.category.name if c.category else 'General',
            'case_type': c.case_type,
            'status': c.status,
            'target_amount': float(c.target_amount),
            'total_raised': float(c.get_total_raised()),
            'progress_percentage': c.get_progress_percentage(),
            'remaining_amount': float(c.get_remaining_amount()),
            'days_remaining': c.get_days_remaining(),
            'is_critical': c.is_critical(),
            'tags': tags_list,
            'story_summary': c.story[:200] + '...' if len(c.story) > 200 else c.story,
            'url': f"/cases/{c.id}/",
        })
    return results

def get_user_campaigns_context(user):
    """
    If the user is authenticated, retrieves a safe summary of their own campaigns.
    Never exposes passwords, tokens, or private data.
    """
    if not user or not user.is_authenticated:
        return None

    user_campaigns = Campaign.objects.filter(owner=user).select_related('category')[:5]
    if not user_campaigns:
        return f"User {user.get_full_name() or user.email} currently has no created campaigns."

    lines = [f"Campaigns created by logged-in user {user.get_full_name() or user.email}:"]
    for c in user_campaigns:
        can_cancel = c.can_creator_cancel(user)
        lines.append(
            f"- ID #{c.id}: '{c.title}' | Status: {c.status} | Target: {c.target_amount} EGP | "
            f"Raised: {c.get_total_raised()} EGP ({c.get_progress_percentage()}%) | "
            f"Eligible to cancel by creator: {'Yes (<25% raised)' if can_cancel else 'No (>=25% raised or not active)'}"
        )
    return "\n".join(lines)

def build_chatbot_context(message_text, user=None):
    """
    Main orchestrator to build a bounded context for Gemini based on the user's inquiry.
    """
    context_parts = []
    
    # 1. Platform overview
    context_parts.append(get_platform_overview_context())

    # 2. Check for recommendation intent
    message_lower = message_text.lower()
    rec_keywords = ['recommend', 'رشح', 'اقتراح', 'مقترح', 'suggest', 'تبرع لمين', 'حالات محتاجة', 'urgent', 'critical', 'حالات حرجة']
    is_rec = any(kw in message_lower for kw in rec_keywords)

    if is_rec:
        recs = get_recommended_campaigns(limit=3)
        if recs:
            lines = ["Top Recommended Live Campaigns from EgyStory Database:"]
            for r in recs:
                lines.append(
                    f"- '{r['title']}' (ID #{r['id']}, Link: {r['url']}): Goal {r['target_amount']:.0f} EGP, "
                    f"Raised {r['total_raised']:.0f} EGP ({r['progress_percentage']}%), "
                    f"Category: {r['category']}, Critical: {'Yes' if r['is_critical'] else 'No'}. "
                    f"Summary: {r['story_summary']}"
                )
            context_parts.append("\n".join(lines))

    # 3. Always search for matching campaigns if the user mentions specific words or campaign topics
    search_results = search_relevant_campaigns(message_text, max_results=4)
    if search_results:
        lines = ["Matching Live Campaigns Found in EgyStory Database:"]
        for r in search_results:
            lines.append(
                f"- '{r['title']}' (ID #{r['id']}, Link: {r['url']}): Goal {r['target_amount']:.0f} EGP, "
                f"Raised {r['total_raised']:.0f} EGP ({r['progress_percentage']}%), "
                f"Category: {r['category']}, Status: {r['status']}, Critical: {'Yes' if r['is_critical'] else 'No'}. "
                f"Summary: {r['story_summary']}"
            )
        context_parts.append("\n".join(lines))
    elif not is_rec and any(w in message_lower for w in ['حالة', 'حالات', 'campaign', 'case', 'story', 'قصة', 'مريض', 'عملية', 'جهاز', 'عروسة', 'عمليات']):
        context_parts.append("Database Search Result: No campaigns matching this specific query were found in the live database.")

    # 4. User context if relevant
    if user and user.is_authenticated:
        user_camps = get_user_campaigns_context(user)
        if user_camps:
            context_parts.append(user_camps)

    return "\n\n".join(context_parts)
