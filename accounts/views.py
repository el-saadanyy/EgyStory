import uuid
# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.contrib import messages
# pyrefly: ignore [missing-import]
from django.contrib.auth import authenticate, login, logout
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required

# pyrefly: ignore [missing-import]
from django.core.mail import send_mail
# pyrefly: ignore [missing-import]
from django.template.loader import render_to_string
# pyrefly: ignore [missing-import]
from django.utils.html import strip_tags
# pyrefly: ignore [missing-import]
from django.conf import settings
import logging

from .models import User, ActivationToken
from .forms import RegistrationForm, LoginForm, ProfileEditForm, DeleteAccountForm

logger = logging.getLogger(__name__)


# ── Registration ───────────────────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = RegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data.get('email')
        existing_user = User.objects.filter(email=email, is_active=False).first()

        if existing_user:
            # Re-use existing inactive user
            user = existing_user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.phone = form.cleaned_data['phone']
            if form.cleaned_data.get('profile_picture'):
                user.profile_picture = form.cleaned_data['profile_picture']
            user.set_password(form.cleaned_data['password'])
            user.save()
            is_new_user = False
        else:
            # Create a completely new user
            user = form.save()
            is_new_user = True

        # Delete any existing activation tokens for this user
        ActivationToken.objects.filter(user=user).delete()
        
        # Create activation token
        token = ActivationToken.objects.create(user=user)

        # Build activation OTP payload
        otp_code = token.token

        # Send activation email (console backend in development)
        subject = 'Activate your EgyStory account'
        html_message = render_to_string('accounts/activation_email.html', {
            'user': user,
            'otp': otp_code,
        })
        plain_message = strip_tags(html_message)

        try:
            sent = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            if not sent:
                raise Exception("Email failed to send (send_mail returned 0)")
                
            request.session['activation_email'] = user.email
            messages.success(
                request,
                f'Account created! We sent a 6-digit verification code to {user.email}. (Please check your Spam/Junk folder if not in Inbox).'
            )
            return redirect('verify_otp')
            
        except Exception as e:
            logger.error(f"SMTP Email Delivery Error during registration: {str(e)}", exc_info=True)
            
            # Clean up the token we just made
            token.delete()
            # Only delete the user if they were just created in this request
            if is_new_user:
                user.delete()
                
            messages.error(
                request,
                'Failed to send the activation email. Please ensure your email is correct and try again.'
            )
            return redirect('register')

    return render(request, 'accounts/register.html', {'form': form})


# ── Activation ─────────────────────────────────────────────────────────────

def activate(request, token):
    try:
        activation_token = ActivationToken.objects.get(token=token)
    except ActivationToken.DoesNotExist:
        return render(request, 'accounts/activation_failed.html', {
            'reason': 'Invalid activation link.'
        })

    if activation_token.is_expired():
        activation_token.delete()
        return render(request, 'accounts/activation_failed.html', {
            'reason': 'This activation link has expired (valid for 24 hours). Please register again.'
        })

    user = activation_token.user
    user.is_active = True
    user.save()
    activation_token.delete()

    messages.success(request, 'Your account has been activated! You can now log in.')
    return render(request, 'accounts/activation_success.html', {'user': user})


def verify_otp(request):
    email = request.session.get('activation_email')
    if not email:
        messages.error(request, 'No pending activation found. Please register or log in.')
        return redirect('login')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return redirect('register')

    if user.is_active:
        messages.info(request, 'Account is already active.')
        return redirect('login')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        try:
            activation_token = ActivationToken.objects.get(user=user, token=otp)
            
            if activation_token.is_expired():
                activation_token.delete()
                messages.error(request, 'This OTP has expired. Please request a new one.')
            else:
                user.is_active = True
                user.save()
                activation_token.delete()
                # Clear session
                if 'activation_email' in request.session:
                    del request.session['activation_email']
                messages.success(request, 'Your account has been activated! You can now log in.')
                return redirect('login')
                
        except ActivationToken.DoesNotExist:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'accounts/verify_otp.html', {'email': email})


def resend_otp(request):
    email = request.session.get('activation_email')
    if not email:
        return redirect('login')
        
    try:
        user = User.objects.get(email=email)
        if user.is_active:
            return redirect('login')
            
        # Delete old token if exists
        ActivationToken.objects.filter(user=user).delete()
        
        # Create new token
        token = ActivationToken.objects.create(user=user)
        
        # Send email
        subject = 'Activate your EgyStory account'
        html_message = render_to_string('accounts/activation_email.html', {
            'user': user,
            'otp': token.token,
        })
        plain_message = strip_tags(html_message)

        try:
            sent = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            if not sent:
                raise Exception("Email failed to send (send_mail returned 0)")
                
            messages.success(request, f'A new verification code has been sent to {email}. (Please check your Spam/Junk folder if not in Inbox).')
        except Exception as e:
            logger.error(f"SMTP Email Delivery Error during resend OTP: {str(e)}", exc_info=True)
            # Delete the token we just created because the email failed
            token.delete()
            messages.error(request, 'Failed to send the activation email. Please try again later.')
            
    except User.DoesNotExist:
        pass
        
    return redirect('verify_otp')


# ── Login ──────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower().strip()
        password = form.cleaned_data['password']

        # Check if the user exists but is not yet activated
        try:
            user_obj = User.objects.get(email=email)
            if not user_obj.is_active:
                request.session['activation_email'] = email
                messages.error(
                    request,
                    'Your account has not been activated yet. '
                    'Please check your email for the 6-digit verification code (including Spam/Junk folder).'
                )
                return render(request, 'accounts/login.html', {
                    'form': form,
                    'unactivated_email': email,
                })
        except User.DoesNotExist:
            pass

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Welcome back! You have been logged in successfully.')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


# ── Logout ─────────────────────────────────────────────────────────────────

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ── Profile ────────────────────────────────────────────────────────────────

@login_required
def profile(request):
    from campaigns.models import Campaign, Donation
    user_campaigns = Campaign.objects.filter(owner=request.user).order_by('-created_at')
    user_donations = Donation.objects.filter(donor_email=request.user.email, is_anonymous=False).order_by('-created_at')
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'user_campaigns': user_campaigns,
        'user_donations': user_donations,
    })


@login_required
def profile_edit(request):
    form = ProfileEditForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        if request.POST.get('clear_avatar') == '1':
            if user.profile_picture:
                user.profile_picture.delete(save=False)
            user.profile_picture = None
        user.save()
        form.save_m2m()
        messages.success(request, 'Your profile has been updated.')
        return redirect('profile')

    return render(request, 'accounts/profile_edit.html', {'form': form})


# ── Account Deletion ───────────────────────────────────────────────────────

@login_required
def delete_account(request):
    form = DeleteAccountForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been permanently deleted.')
        return redirect('home')

    return render(request, 'accounts/delete_confirm.html', {'form': form})
