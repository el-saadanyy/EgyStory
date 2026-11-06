from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.core.mail import EmailMessage, EmailMultiAlternatives
from accounts.models import User
from egystory.email_backends import ResendEmailBackend, BrevoEmailBackend


class DemoAccountCommandTests(TestCase):
    def test_setup_demo_accounts_creates_users_with_proper_roles_when_passwords_provided(self):
        call_command(
            'setup_demo_accounts',
            user_email='demouser@test.com',
            user_password='SecureUserPwd123!',
            reviewer_email='demoreviewer@test.com',
            reviewer_password='SecureReviewerPwd123!',
        )

        user = User.objects.get(email='demouser@test.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('SecureUserPwd123!'))

        reviewer = User.objects.get(email='demoreviewer@test.com')
        self.assertTrue(reviewer.is_active)
        self.assertTrue(reviewer.is_staff)
        self.assertFalse(reviewer.is_superuser)  # Must never be superuser
        self.assertTrue(reviewer.check_password('SecureReviewerPwd123!'))

    def test_setup_demo_accounts_skips_when_passwords_missing(self):
        call_command(
            'setup_demo_accounts',
            user_email='nopassword_user@test.com',
            user_password='',
            reviewer_email='nopassword_reviewer@test.com',
            reviewer_password='',
        )
        self.assertFalse(User.objects.filter(email='nopassword_user@test.com').exists())
        self.assertFalse(User.objects.filter(email='nopassword_reviewer@test.com').exists())

    def test_setup_demo_accounts_is_idempotent(self):
        # Run once
        call_command(
            'setup_demo_accounts',
            user_email='idempotent_user@test.com',
            user_password='InitialPwd123!',
            reviewer_email='idempotent_reviewer@test.com',
            reviewer_password='InitialRevPwd123!',
        )
        user_before = User.objects.get(email='idempotent_user@test.com')

        # Run twice
        call_command(
            'setup_demo_accounts',
            user_email='idempotent_user@test.com',
            user_password='InitialPwd123!',
            reviewer_email='idempotent_reviewer@test.com',
            reviewer_password='InitialRevPwd123!',
        )
        user_after = User.objects.get(email='idempotent_user@test.com')
        self.assertEqual(user_before.pk, user_after.pk)
        self.assertTrue(user_after.check_password('InitialPwd123!'))


class HttpEmailBackendTests(TestCase):
    @patch('requests.post')
    def test_resend_email_backend_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        backend = ResendEmailBackend(api_key='re_test_12345')
        msg = EmailMultiAlternatives(
            subject='Welcome',
            body='Plain text body',
            from_email='onboarding@resend.dev',
            to=['recipient@example.com'],
        )
        msg.attach_alternative('<p>HTML body</p>', 'text/html')

        sent = backend.send_messages([msg])
        self.assertEqual(sent, 1)
        self.assertTrue(mock_post.called)
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['to'], ['recipient@example.com'])
        self.assertEqual(call_kwargs['json']['html'], '<p>HTML body</p>')

    @patch('requests.post')
    def test_resend_email_backend_handles_test_mode_restriction(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = '{"message": "You can only send testing emails to your own email address"}'
        mock_post.return_value = mock_response

        backend = ResendEmailBackend(api_key='re_test_12345', fail_silently=True)
        msg = EmailMessage(
            subject='Test',
            body='Body',
            from_email='onboarding@resend.dev',
            to=['unverified@example.com'],
        )

        sent = backend.send_messages([msg])
        self.assertEqual(sent, 0)  # Must not report as delivered when error occurred

    @patch('requests.post')
    def test_brevo_email_backend_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        backend = BrevoEmailBackend(api_key='xkeysib-test-12345')
        msg = EmailMessage(
            subject='Reset OTP',
            body='Your OTP is 123456',
            from_email='onboarding@resend.dev',
            to=['user@example.com'],
        )

        sent = backend.send_messages([msg])
        self.assertEqual(sent, 1)
        self.assertTrue(mock_post.called)
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['to'], [{'email': 'user@example.com'}])
