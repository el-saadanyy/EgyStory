import uuid
# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# pyrefly: ignore [missing-import]
from django.core.validators import RegexValidator
# pyrefly: ignore [missing-import]
from django.utils import timezone


# ── Egyptian phone validator ───────────────────────────────────────────────
egyptian_phone_validator = RegexValidator(
    regex=r'^01[0125][0-9]{8}$',
    message='Enter a valid Egyptian mobile number (e.g. 01012345678).',
)


# ── Custom Manager ─────────────────────────────────────────────────────────
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


from django.core.exceptions import ValidationError
import re


def validate_birthdate_not_future(value):
    if value and value > timezone.now().date():
        raise ValidationError('Birthdate cannot be in the future.')


def validate_facebook_url(value):
    if value:
        pattern = r'^https?://([a-z0-9-]+\.)*facebook\.com/.*$'
        if not re.match(pattern, value, re.IGNORECASE):
            raise ValidationError('Enter a valid Facebook profile URL (e.g. https://facebook.com/yourprofile).')


# ── Custom User Model ──────────────────────────────────────────────────────
class User(AbstractBaseUser, PermissionsMixin):
    """
    EgyStory custom user model.
    Authentication is done via email + password.
    Account is inactive until the user clicks the activation link.
    """

    email = models.EmailField(
        unique=True,
        verbose_name='Email address',
    )
    first_name = models.CharField(max_length=50, verbose_name='First name')
    last_name = models.CharField(max_length=50, verbose_name='Last name')
    phone = models.CharField(
        max_length=15,
        validators=[egyptian_phone_validator],
        verbose_name='Mobile phone',
    )
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        verbose_name='Profile picture',
    )
    birthdate = models.DateField(
        blank=True,
        null=True,
        verbose_name='Birthdate',
        validators=[validate_birthdate_not_future],
    )
    facebook = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Facebook profile',
        validators=[validate_facebook_url],
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Country',
    )

    # Account state
    is_active = models.BooleanField(
        default=False,  # Requires email activation before login
        verbose_name='Active',
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff / Admin',
    )

    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Date joined')

    objects = UserManager()

    # Use email as the login identifier instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name


import random

def generate_otp():
    """Generates a 6-digit OTP string."""
    return str(random.randint(100000, 999999))

# ── Activation Token ───────────────────────────────────────────────────────
class ActivationToken(models.Model):
    """
    One-time token sent via email for account activation.
    Expires 24 hours after creation.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='activation_token',
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_otp,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Activation Token'

    def __str__(self):
        return f'Token for {self.user.email}'

    def is_expired(self):
        """Returns True if the token is older than 24 hours."""
        expiry = self.created_at + timezone.timedelta(hours=24)
        return timezone.now() > expiry
