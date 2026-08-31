import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import User


EGYPTIAN_PHONE_REGEX = r'^01[0125][0-9]{8}$'

ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
MAX_IMAGE_SIZE_MB = 5


def validate_profile_picture(image):
    """Validate image size and type."""
    if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f'Image must be smaller than {MAX_IMAGE_SIZE_MB}MB.')
    if hasattr(image, 'content_type') and image.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError('Only JPEG, PNG, GIF, and WebP images are allowed.')


from django.utils import timezone


def validate_facebook_input(facebook):
    if facebook:
        facebook = facebook.strip()
        pattern = r'^https?://([a-z0-9-]+\.)*facebook\.com/.*$'
        if not re.match(pattern, facebook, re.IGNORECASE):
            raise ValidationError('Enter a valid Facebook profile URL (e.g. https://facebook.com/yourprofile).')
    return facebook


def validate_birthdate_input(birthdate):
    if birthdate and birthdate > timezone.now().date():
        raise ValidationError('Birthdate cannot be in the future.')
    return birthdate


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'autocomplete': 'new-password'}),
        min_length=8,
        label='Password',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password', 'autocomplete': 'new-password'}),
        label='Confirm password',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_picture', 'birthdate', 'facebook', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address', 'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={'placeholder': '01012345678'}),
            'profile_picture': forms.FileInput(attrs={'id': 'avatar-input', 'style': 'display: none;', 'accept': 'image/*'}),
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
            'facebook': forms.URLInput(attrs={'placeholder': 'https://facebook.com/yourprofile'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country'}),
        }

    def validate_unique(self):
        # Skip the model's default unique validation for this form
        # because we handle custom active/inactive unique validation in clean_email.
        pass

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        user = User.objects.filter(email=email).first()
        if user and user.is_active:
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.match(EGYPTIAN_PHONE_REGEX, phone):
            raise ValidationError('Enter a valid Egyptian mobile number (e.g. 01012345678).')
        return phone

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image:
            validate_profile_picture(image)
        return image

    def clean_birthdate(self):
        return validate_birthdate_input(self.cleaned_data.get('birthdate'))

    def clean_facebook(self):
        return validate_facebook_input(self.cleaned_data.get('facebook'))

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_active = False  # Requires email activation
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email address', 'autocomplete': 'email'}),
        label='Email',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'autocomplete': 'current-password'}),
        label='Password',
    )


class ProfileEditForm(forms.ModelForm):
    """Edit profile — email is intentionally excluded (cannot be changed)."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'profile_picture', 'birthdate', 'facebook', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'phone': forms.TextInput(attrs={'placeholder': '01012345678'}),
            'profile_picture': forms.FileInput(attrs={'id': 'avatar-input', 'style': 'display: none;', 'accept': 'image/*'}),
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
            'facebook': forms.URLInput(attrs={'placeholder': 'https://facebook.com/yourprofile'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.match(EGYPTIAN_PHONE_REGEX, phone):
            raise ValidationError('Enter a valid Egyptian mobile number (e.g. 01012345678).')
        return phone

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image and hasattr(image, 'size'):
            validate_profile_picture(image)
        return image

    def clean_birthdate(self):
        return validate_birthdate_input(self.cleaned_data.get('birthdate'))

    def clean_facebook(self):
        return validate_facebook_input(self.cleaned_data.get('facebook'))


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your current password',
            'autocomplete': 'current-password',
        }),
        label='Current Password',
        error_messages={'required': 'Please enter your current password to confirm deletion.'},
    )
    confirm = forms.BooleanField(
        required=True,
        label='I understand this action is permanent and cannot be undone.',
        error_messages={'required': 'You must confirm to delete your account.'},
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and self.user:
            if not self.user.check_password(password):
                raise forms.ValidationError('Incorrect password. Please enter your current password.')
        return password
