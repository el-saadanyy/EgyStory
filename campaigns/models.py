# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.conf import settings
# pyrefly: ignore [missing-import]
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator

class CampaignStatus(models.TextChoices):
    PENDING = 'Pending Review', 'Pending Review'
    ACTIVE = 'Active', 'Active'
    COMPLETED = 'Completed', 'Completed'
    EXPIRED = 'Expired', 'Expired'
    CANCELLED = 'Cancelled', 'Cancelled'

class CaseType(models.TextChoices):
    NORMAL = 'Normal', 'Normal'
    RARE = 'Rare / Ultra-Rare & High-Cost', 'Rare / Ultra-Rare & High-Cost'

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Campaign(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaigns')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    tags = models.ManyToManyField(Tag, blank=True, related_name='campaigns')
    title = models.CharField(max_length=255)
    story = models.TextField()
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    initial_raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Amount Raised So Far', null=True, blank=True)
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    campaign_image = models.ImageField(upload_to='campaigns/')
    case_type = models.CharField(max_length=50, choices=CaseType.choices, default=CaseType.NORMAL)
    status = models.CharField(max_length=50, choices=CampaignStatus.choices, default=CampaignStatus.PENDING)
    deadline = models.DateField(null=True, blank=True)
    supporting_document = models.FileField(upload_to='campaigns/documents/', null=True, blank=True)
    is_manual_critical = models.BooleanField(default=False, verbose_name="Manually Marked Critical")
    is_featured = models.BooleanField(default=False, verbose_name="Featured Campaign")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_progress_percentage(self):
        if self.target_amount <= 0:
            return 100
        initial = self.initial_raised_amount or Decimal('0.00')
        total_raised = self.raised_amount + initial
        progress = (total_raised / self.target_amount) * 100
        
        if progress >= 100:
            return 100
        elif progress == 0:
            return 0
        elif progress < 1:
            return round(float(progress), 3)
        else:
            if progress % 1 == 0:
                return int(progress)
            return round(float(progress), 1)
    
    def get_total_raised(self):
        initial = self.initial_raised_amount or Decimal('0.00')
        return self.raised_amount + initial
    
    def get_remaining_amount(self):
        initial = self.initial_raised_amount or Decimal('0.00')
        total_raised = self.raised_amount + initial
        remaining = self.target_amount - total_raised
        return max(remaining, Decimal('0.00'))
    
    def get_days_remaining(self):
        if not self.deadline:
            return None
        delta = self.deadline - timezone.now().date()
        return max(delta.days, 0)

    def is_expired(self):
        if self.deadline and self.deadline < timezone.now().date():
            return True
        return False

    def can_creator_cancel(self, user):
        """
        A creator can cancel their campaign ONLY if:
        - user is authenticated and is the owner of the campaign
        - campaign status is Active or Pending (not already Cancelled, Completed, or Expired)
        - raised amount (get_total_raised()) is strictly LESS THAN 25% of target_amount (< 25%)
        """
        if not user or not user.is_authenticated:
            return False
        if self.owner_id != user.id:
            return False
        if self.status not in [CampaignStatus.PENDING, CampaignStatus.ACTIVE]:
            return False
        if self.target_amount <= 0:
            return False
        
        total_raised = self.get_total_raised()
        threshold = self.target_amount * Decimal('0.25')
        return total_raised < threshold


    def get_urgency_score(self):
        score = 0
        
        # Factor 1: Deadline Proximity
        days_remaining = self.get_days_remaining()
        if days_remaining is not None:
            if days_remaining <= 7:
                score += 40
            elif days_remaining <= 30:
                score += 30
            elif days_remaining <= 60:
                score += 20
            elif days_remaining <= 120:
                score += 10
            else:
                score += 5
        
        # Factor 2: Remaining Amount Ratio
        progress = self.get_progress_percentage()
        if progress >= 90:
            score += 30
        elif progress >= 75:
            score += 25
        elif progress >= 50:
            score += 15
        elif progress >= 25:
            score += 10
        else:
            score += 5

        # Factor 3: Required Daily Funding Rate (only in final 30 days)
        if days_remaining is not None and days_remaining <= 30:
            remaining_amount = self.get_remaining_amount()
            days_for_rate = max(days_remaining, 1)
            daily_rate = remaining_amount / Decimal(days_for_rate)
            
            if self.target_amount > 0:
                rate_percentage = (daily_rate / self.target_amount) * 100
                if rate_percentage >= 5:
                    score += 30
                elif rate_percentage >= 2:
                    score += 20
                elif rate_percentage >= 1:
                    score += 10
                else:
                    score += 5
        
        return min(score, 100)

    def is_auto_critical(self):
        """Check if campaign reaches automatic critical urgency threshold."""
        return self.get_urgency_score() >= 70

    def is_critical(self):
        """Campaign is Critical if manually overridden OR automatically urgent."""
        return self.is_manual_critical or self.is_auto_critical()

    def get_average_rating(self):
        avg = self.ratings.aggregate(models.Avg('score'))['score__avg']
        if avg is None:
            return 0.0
        return round(float(avg), 1)

    def get_rating_count(self):
        return self.ratings.count()

    def get_star_rating_data(self):
        avg = self.get_average_rating()
        full_stars = int(avg)
        has_half_star = (avg - full_stars) >= 0.3
        empty_stars = 5 - full_stars - (1 if has_half_star else 0)
        return {
            'average': avg,
            'full_stars': range(full_stars),
            'has_half_star': has_half_star,
            'empty_stars': range(max(0, empty_stars)),
            'count': self.get_rating_count()
        }

class Donation(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='donations')
    donor_name = models.CharField(max_length=255)
    donor_email = models.EmailField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} to {self.campaign.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Update Campaign safely
            campaign = self.campaign
            campaign.raised_amount += self.amount
            if campaign.get_total_raised() >= campaign.target_amount and campaign.status == CampaignStatus.ACTIVE:
                campaign.status = CampaignStatus.COMPLETED

            campaign.save(update_fields=['raised_amount', 'status'])

class CampaignUpdate(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='updates')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class CampaignImage(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='campaigns/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Image for {self.campaign.title}"

class CampaignRating(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaign_ratings')
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('campaign', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} rated {self.campaign.title} - {self.score}/5"

class ReportReason(models.TextChoices):
    FRAUD = 'Fraud or Misleading', 'Fraud or Misleading Information'
    INAPPROPRIATE = 'Inappropriate Content', 'Inappropriate Content'
    SPAM = 'Spam or Scam', 'Spam or Scam'
    OTHER = 'Other', 'Other'

class ReportStatus(models.TextChoices):
    PENDING = 'Pending Review', 'Pending Review'
    REVIEWED = 'Reviewed', 'Reviewed'
    DISMISSED = 'Dismissed', 'Dismissed'
    ACTION_TAKEN = 'Action Taken', 'Action Taken'

class CampaignReport(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_reports')
    reason = models.CharField(max_length=50, choices=ReportReason.choices, default=ReportReason.OTHER)
    details = models.TextField(help_text="Detailed description of the issue.")
    status = models.CharField(max_length=50, choices=ReportStatus.choices, default=ReportStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.id} for {self.campaign.title} ({self.status})"

class Comment(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaign_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        if self.parent:
            return f"Reply by {self.user} on comment #{self.parent.id}"
        return f"Comment by {self.user} on {self.campaign.title}"

    @property
    def is_reply(self):
        return self.parent is not None


class CommentReport(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_comments')
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comment', 'reporter')
        ordering = ['-created_at']

    def __str__(self):
        return f"Report on Comment #{self.comment.id} by {self.reporter}"

