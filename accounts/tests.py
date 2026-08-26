from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import User, ActivationToken

class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.verify_url = reverse('verify_otp')
        self.resend_url = reverse('resend_otp')
        self.login_url = reverse('login')
        self.test_email = 'testuser@example.com'
        self.test_password = 'TestPassword123'
        self.valid_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': self.test_email,
            'phone': '01012345678',
            'password': self.test_password,
            'confirm_password': self.test_password,
        }

    def test_registration_creates_inactive_user(self):
        response = self.client.post(self.register_url, self.valid_data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email=self.test_email)
        self.assertFalse(user.is_active)

    def test_registration_creates_otp(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        self.assertTrue(ActivationToken.objects.filter(user=user).exists())

    def test_registration_stores_activation_email_in_session(self):
        self.client.post(self.register_url, self.valid_data)
        self.assertEqual(self.client.session.get('activation_email'), self.test_email)

    def test_otp_verification_with_correct_code_activates_user(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        token = ActivationToken.objects.get(user=user).token
        
        response = self.client.post(self.verify_url, {'otp': token})
        self.assertEqual(response.status_code, 302) # Redirects to login
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_invalid_otp_does_not_activate_user(self):
        self.client.post(self.register_url, self.valid_data)
        response = self.client.post(self.verify_url, {'otp': '000000'})
        self.assertEqual(response.status_code, 200) # Stays on page with error
        user = User.objects.get(email=self.test_email)
        self.assertFalse(user.is_active)

    def test_expired_otp_does_not_activate_user(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        activation_token = ActivationToken.objects.get(user=user)
        # Manually expire the token
        activation_token.created_at = timezone.now() - timezone.timedelta(hours=25)
        activation_token.save()
        
        response = self.client.post(self.verify_url, {'otp': activation_token.token})
        self.assertEqual(response.status_code, 200) # Stays on page with error
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_successful_verification_removes_activation_token(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        token = ActivationToken.objects.get(user=user).token
        
        self.client.post(self.verify_url, {'otp': token})
        self.assertFalse(ActivationToken.objects.filter(user=user).exists())

    def test_successful_verification_clears_activation_session(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        token = ActivationToken.objects.get(user=user).token
        
        self.client.post(self.verify_url, {'otp': token})
        self.assertNotIn('activation_email', self.client.session)

    def test_resend_otp_replaces_old_token(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        old_token_obj = ActivationToken.objects.get(user=user)
        old_token = old_token_obj.token
        old_pk = old_token_obj.pk
        
        response = self.client.get(self.resend_url)
        self.assertEqual(response.status_code, 302)
        
        new_token_obj = ActivationToken.objects.get(user=user)
        self.assertNotEqual(old_pk, new_token_obj.pk)

    def test_inactive_users_cannot_log_in(self):
        self.client.post(self.register_url, self.valid_data)
        response = self.client.post(self.login_url, {
            'email': self.test_email,
            'password': self.test_password
        })
        self.assertEqual(response.status_code, 200) # Stay on login page
        # User shouldn't be authenticated
        from django.contrib.auth import get_user
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_active_users_can_log_in_with_correct_credentials(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        user.is_active = True
        user.save()
        
        response = self.client.post(self.login_url, {
            'email': self.test_email,
            'password': self.test_password
        })
        self.assertEqual(response.status_code, 302) # Redirect to home
        from django.contrib.auth import get_user
        self.assertTrue(get_user(self.client).is_authenticated)

    def test_successful_login_displays_notification(self):
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        user.is_active = True
        user.save()

        response = self.client.post(self.login_url, {
            'email': self.test_email,
            'password': self.test_password
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('Welcome back! You have been logged in successfully.' in str(m) for m in messages_list))

    def test_registration_with_existing_active_user_fails(self):
        # Register and activate
        self.client.post(self.register_url, self.valid_data)
        user = User.objects.get(email=self.test_email)
        user.is_active = True
        user.save()

        # Try registering again
        response = self.client.post(self.register_url, self.valid_data)
        self.assertEqual(response.status_code, 200) # Form error
        self.assertIn('An account with this email already exists.', response.context['form'].errors.get('email', []))

    def test_registration_with_existing_inactive_user_updates_details(self):
        # Register initially
        self.client.post(self.register_url, self.valid_data)
        initial_user = User.objects.get(email=self.test_email)
        initial_pk = initial_user.pk
        initial_token = ActivationToken.objects.get(user=initial_user).token

        # Modify valid_data for second registration
        new_data = self.valid_data.copy()
        new_data['first_name'] = 'Updated'
        new_data['last_name'] = 'Name'
        new_data['password'] = 'NewPassword123'
        new_data['confirm_password'] = 'NewPassword123'

        response = self.client.post(self.register_url, new_data)
        self.assertEqual(response.status_code, 302) # Success redirect to verify_otp
        
        # Verify it updated the SAME user and didn't create a new one
        self.assertEqual(User.objects.filter(email=self.test_email).count(), 1)
        updated_user = User.objects.get(email=self.test_email)
        self.assertEqual(updated_user.pk, initial_pk)
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertTrue(updated_user.check_password('NewPassword123'))
        
        # Verify it created a NEW token
        new_token = ActivationToken.objects.get(user=updated_user).token
        self.assertNotEqual(initial_token, new_token)


from datetime import date, timedelta
from django.core.exceptions import ValidationError
from accounts.forms import ProfileEditForm, RegistrationForm


class UserProfileFieldsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='profileuser@example.com',
            password='TestPassword123',
            first_name='Profile',
            last_name='Tester',
            phone='01012345678',
            is_active=True
        )
        self.profile_url = reverse('profile')
        self.profile_edit_url = reverse('profile_edit')

    def test_user_can_exist_without_optional_fields(self):
        self.assertIsNone(self.user.birthdate)
        self.assertIsNone(self.user.facebook)
        self.assertIsNone(self.user.country)

    def test_user_can_contain_birthdate_facebook_and_country(self):
        bdate = date(1995, 5, 15)
        fb_url = 'https://facebook.com/profileuser'
        country_name = 'Egypt'
        self.user.birthdate = bdate
        self.user.facebook = fb_url
        self.user.country = country_name
        self.user.full_clean()
        self.user.save()

        fetched = User.objects.get(pk=self.user.pk)
        self.assertEqual(fetched.birthdate, bdate)
        self.assertEqual(fetched.facebook, fb_url)
        self.assertEqual(fetched.country, country_name)

    def test_future_birthdate_rejected(self):
        future_date = date.today() + timedelta(days=10)
        self.user.birthdate = future_date
        with self.assertRaises(ValidationError):
            self.user.full_clean()

        form_data = {
            'first_name': 'Profile',
            'last_name': 'Tester',
            'phone': '01012345678',
            'birthdate': future_date.strftime('%Y-%m-%d'),
        }
        form = ProfileEditForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('birthdate', form.errors)

    def test_facebook_url_validation(self):
        # Invalid facebook URL
        form_data_invalid = {
            'first_name': 'Profile',
            'last_name': 'Tester',
            'phone': '01012345678',
            'facebook': 'https://notfacebook.com/user',
        }
        form_invalid = ProfileEditForm(data=form_data_invalid, instance=self.user)
        self.assertFalse(form_invalid.is_valid())
        self.assertIn('facebook', form_invalid.errors)

        # Valid facebook URL
        form_data_valid = {
            'first_name': 'Profile',
            'last_name': 'Tester',
            'phone': '01012345678',
            'facebook': 'https://www.facebook.com/validuser',
        }
        form_valid = ProfileEditForm(data=form_data_valid, instance=self.user)
        self.assertTrue(form_valid.is_valid())

    def test_profile_editing_supports_new_fields(self):
        self.client.force_login(self.user)
        post_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'phone': '01212345678',
            'birthdate': '1990-10-20',
            'facebook': 'https://facebook.com/updatedprofile',
            'country': 'Egypt',
        }
        response = self.client.post(self.profile_edit_url, post_data)
        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.birthdate, date(1990, 10, 20))
        self.assertEqual(self.user.facebook, 'https://facebook.com/updatedprofile')
        self.assertEqual(self.user.country, 'Egypt')

        # Also check profile display contains values and clickable link
        profile_resp = self.client.get(self.profile_url)
        self.assertEqual(profile_resp.status_code, 200)
        self.assertContains(profile_resp, '20 Oct 1990')
        self.assertContains(profile_resp, 'Egypt')
        self.assertContains(profile_resp, 'href="https://facebook.com/updatedprofile"')
        self.assertContains(profile_resp, 'target="_blank"')
        self.assertContains(profile_resp, 'rel="noopener noreferrer"')

    def test_existing_registration_flow_unaffected(self):
        reg_url = reverse('register')
        reg_data = {
            'first_name': 'NewReg',
            'last_name': 'User',
            'email': 'newreg@example.com',
            'phone': '01112345678',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        }
        response = self.client.post(reg_url, reg_data)
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(email='newreg@example.com')
        self.assertFalse(new_user.is_active)
        self.assertIsNone(new_user.birthdate)
        self.assertIsNone(new_user.facebook)
        self.assertIsNone(new_user.country)

    def test_existing_user_data_unaffected(self):
        old_user = User.objects.create_user(
            email='olduser@example.com',
            password='OldPassword123',
            first_name='Old',
            last_name='User',
            phone='01512345678',
            is_active=True
        )
        self.assertEqual(old_user.email, 'olduser@example.com')
        self.assertTrue(old_user.check_password('OldPassword123'))
        self.assertTrue(old_user.is_active)
        self.assertIsNone(old_user.birthdate)
        self.assertIsNone(old_user.facebook)
        self.assertIsNone(old_user.country)


class PasswordProtectedAccountDeletionTests(TestCase):
    def setUp(self):
        self.password = 'SecureUserPass123!'
        self.user = User.objects.create_user(
            email='delete_test_user@egystory.com',
            password=self.password,
            first_name='Delete',
            last_name='Tester',
            phone='01099998888',
            is_active=True
        )
        self.delete_url = reverse('delete_account')

    def test_unauthenticated_user_cannot_access_or_delete_account(self):
        # GET access denied / redirected to login
        get_response = self.client.get(self.delete_url)
        self.assertEqual(get_response.status_code, 302)
        self.assertIn('/accounts/login/', get_response.url)

        # POST deletion denied / redirected to login
        post_response = self.client.post(self.delete_url, {'confirm': 'on', 'password': self.password})
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_authenticated_user_can_access_delete_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/delete_confirm.html')

    def test_empty_password_prevents_account_deletion(self):
        self.client.force_login(self.user)
        response = self.client.post(self.delete_url, {'confirm': 'on', 'password': ''})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertFormError(response.context['form'], 'password', 'Please enter your current password to confirm deletion.')

    def test_incorrect_password_prevents_account_deletion(self):
        self.client.force_login(self.user)
        response = self.client.post(self.delete_url, {'confirm': 'on', 'password': 'WrongPassword123'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertFormError(response.context['form'], 'password', 'Incorrect password. Please enter your current password.')

    def test_correct_password_deletes_own_account(self):
        self.client.force_login(self.user)
        response = self.client.post(self.delete_url, {'confirm': 'on', 'password': self.password})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_user_cannot_delete_another_user_account(self):
        other_user = User.objects.create_user(
            email='other_user@egystory.com',
            password='OtherUserPass123!',
            first_name='Other',
            last_name='User',
            phone='01011112222',
            is_active=True
        )
        self.client.force_login(self.user)
        self.client.post(self.delete_url, {'confirm': 'on', 'password': self.password})
        self.assertTrue(User.objects.filter(pk=other_user.pk).exists())

