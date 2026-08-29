from django.contrib import admin
from .models import Campaign, Category, Tag, Donation, CampaignUpdate, CampaignImage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

class CampaignImageInline(admin.TabularInline):
    model = CampaignImage
    extra = 1

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'status', 'case_type', 'is_featured', 'target_amount', 'raised_amount', 'created_at')
    list_filter = ('status', 'is_featured', 'case_type', 'category', 'tags')
    search_fields = ('title', 'story', 'tags__name')
    filter_horizontal = ('tags',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'owner', 'category', 'tags', 'story')
        }),
        ('Funding & Details', {
            'fields': ('target_amount', 'initial_raised_amount', 'raised_amount', 'case_type', 'status', 'deadline', 'is_manual_critical', 'is_featured')
        }),
        ('Media & Documents', {
            'fields': ('campaign_image', 'supporting_document')
        }),
    )
    inlines = [CampaignImageInline]

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'amount', 'campaign', 'created_at')
    search_fields = ('donor_name', 'donor_email', 'campaign__title')

@admin.register(CampaignUpdate)
class CampaignUpdateAdmin(admin.ModelAdmin):
    list_display = ('title', 'campaign', 'created_at')

@admin.register(CampaignImage)
class CampaignImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'created_at')

