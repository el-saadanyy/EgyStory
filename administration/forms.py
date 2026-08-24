from django import forms
from django.contrib.auth import get_user_model
from accounts.models import egyptian_phone_validator

User = get_user_model()

class AdminUserForm(forms.ModelForm):
    """
    Form for creating and editing admin users.
    Includes password fields for creation.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        required=False,
        help_text="Required when creating a new admin. Leave blank when editing to keep current password."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'is_active', 'is_superuser']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile phone'}),
            'is_active': forms.CheckboxInput(),
            'is_superuser': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        self.is_creation = kwargs.pop('is_creation', False)
        super().__init__(*args, **kwargs)
        if self.is_creation:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True # Ensure they are staff
        
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
            
        if commit:
            user.save()
        return user


class AdminPasswordResetForm(forms.Form):
    """
    Form for a Superuser to forcefully reset an admin's password.
    """
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("new_password")
        cpwd = cleaned_data.get("confirm_password")
        if pwd and cpwd and pwd != cpwd:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
