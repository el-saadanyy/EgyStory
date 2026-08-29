from django import forms
from decimal import Decimal
from .models import Campaign, Donation, CaseType, Category, Tag

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class CampaignForm(forms.ModelForm):
    supporting_document = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-input'}), required=False, allow_empty_file=True)
    images = MultipleFileField(widget=MultipleFileInput(attrs={'class': 'form-input'}), required=False, label="Additional Pictures")

    class Meta:
        model = Campaign
        fields = ['title', 'category', 'tags', 'story', 'target_amount', 'initial_raised_amount', 'campaign_image', 'case_type', 'deadline', 'supporting_document']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Medical treatment for a child'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'tags': forms.CheckboxSelectMultiple(),
            'story': forms.Textarea(attrs={'class': 'form-input', 'rows': 6, 'placeholder': 'Tell your story...'}),
            'target_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'initial_raised_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'case_type': forms.Select(attrs={'class': 'form-input'}),
            'deadline': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'campaign_image': forms.FileInput(attrs={'class': 'form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        case_type = cleaned_data.get('case_type')
        deadline = cleaned_data.get('deadline')
        supporting_document = cleaned_data.get('supporting_document')
        target_amount = cleaned_data.get('target_amount')
        initial_raised_amount = cleaned_data.get('initial_raised_amount')
        
        # Safely default initial_raised_amount if it's missing or evaluated to None
        if initial_raised_amount is None:
            initial_raised_amount = Decimal('0.00')
            cleaned_data['initial_raised_amount'] = initial_raised_amount
            # Remove any validation error that might have been added by the field for being empty
            if 'initial_raised_amount' in self._errors:
                del self._errors['initial_raised_amount']

        if target_amount is not None and target_amount <= 0:
            self.add_error('target_amount', 'Target amount must be greater than zero.')
            
        if initial_raised_amount is not None and initial_raised_amount < 0:
            self.add_error('initial_raised_amount', 'Amount raised so far cannot be negative.')
            
        if initial_raised_amount is not None and target_amount is not None and initial_raised_amount > target_amount:
            self.add_error('initial_raised_amount', 'Amount raised so far cannot exceed the target amount.')

        if case_type == CaseType.RARE:
            if not deadline:
                self.add_error('deadline', 'Deadline is required for Rare/High-Cost cases.')
            if not supporting_document:
                self.add_error('supporting_document', 'Supporting document is required for Rare/High-Cost cases.')
        
        return cleaned_data

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['donor_name', 'donor_email', 'amount', 'is_anonymous']
        widgets = {
            'donor_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your full name'}),
            'donor_email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'your.email@example.com'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '1'}),
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Donation amount must be greater than zero.")
        return amount

from .models import CampaignRating, CampaignReport

class RatingForm(forms.ModelForm):
    class Meta:
        model = CampaignRating
        fields = ['score']
        widgets = {
            'score': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'rating-score-input'}),
        }

    def clean_score(self):
        score = self.cleaned_data.get('score')
        if not score or score < 1 or score > 5:
            raise forms.ValidationError("Rating score must be an integer between 1 and 5.")
        return score

class ReportForm(forms.ModelForm):
    class Meta:
        model = CampaignReport
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-input'}),
            'details': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Describe why you are reporting this campaign...'}),
        }

    def clean_details(self):
        details = self.cleaned_data.get('details', '').strip()
        if len(details) < 10:
            raise forms.ValidationError("Please provide a detailed explanation (at least 10 characters).")
        return details


