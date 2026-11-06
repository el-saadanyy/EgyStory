import logging
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from decouple import config

logger = logging.getLogger(__name__)


def _extract_email_contents(message):
    """Helper to extract text and html bodies from Django EmailMessage."""
    text_content = message.body or ''
    html_content = None

    if getattr(message, 'alternatives', None):
        for content, mimetype in message.alternatives:
            if mimetype == 'text/html':
                html_content = content
                break

    if not html_content and getattr(message, 'content_subtype', '') == 'html':
        html_content = message.body

    from_email = message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
    return from_email, text_content, html_content


class ResendEmailBackend(BaseEmailBackend):
    """
    HTTP-based email backend for Resend (https://resend.com).
    Bypasses SMTP port restrictions on Render Free tier (uses HTTPS / port 443).
    """

    def __init__(self, api_key=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, 'RESEND_API_KEY', None) or config('RESEND_API_KEY', default='').strip()
        self.api_url = 'https://api.resend.com/emails'

    def send_messages(self, email_messages):
        if not self.api_key:
            msg = 'RESEND_API_KEY is not configured.'
            logger.error(msg)
            if not self.fail_silently:
                raise ValueError(msg)
            return 0

        sent_count = 0
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        for message in email_messages:
            from_email, text_body, html_body = _extract_email_contents(message)
            payload = {
                'from': from_email,
                'to': list(message.to),
                'subject': message.subject,
                'text': text_body,
            }
            if html_body:
                payload['html'] = html_body

            try:
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
                if response.status_code in (200, 201):
                    sent_count += 1
                else:
                    err_text = response.text
                    # Detect Resend testing-mode restriction (free tier only permits sending to account owner email)
                    if response.status_code in (403, 422) and 'testing emails' in err_text.lower():
                        logger.warning(
                            f'Resend testing-mode restriction: Cannot deliver email to {message.to}. '
                            f'In Resend test mode without a verified domain, emails can only be sent '
                            f'to the email address associated with your Resend account. API response: {err_text}'
                        )
                    else:
                        logger.error(f'Resend API error [{response.status_code}]: {err_text}')

                    if not self.fail_silently:
                        response.raise_for_status()
            except Exception as e:
                logger.error(f'Failed to send email via Resend API: {e}', exc_info=True)
                if not self.fail_silently:
                    raise

        return sent_count


class BrevoEmailBackend(BaseEmailBackend):
    """
    HTTP-based email backend for Brevo / Sendinblue (https://brevo.com).
    Bypasses SMTP port restrictions on Render Free tier (uses HTTPS / port 443).
    """

    def __init__(self, api_key=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, 'BREVO_API_KEY', None) or config('BREVO_API_KEY', default='').strip()
        self.api_url = 'https://api.brevo.com/v3/smtp/email'

    def send_messages(self, email_messages):
        if not self.api_key:
            msg = 'BREVO_API_KEY is not configured.'
            logger.error(msg)
            if not self.fail_silently:
                raise ValueError(msg)
            return 0

        sent_count = 0
        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        for message in email_messages:
            from_email, text_body, html_body = _extract_email_contents(message)
            payload = {
                'sender': {'email': from_email},
                'to': [{'email': recipient} for recipient in message.to],
                'subject': message.subject,
                'textContent': text_body,
            }
            if html_body:
                payload['htmlContent'] = html_body

            try:
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
                if response.status_code in (200, 201):
                    sent_count += 1
                else:
                    logger.error(f'Brevo API error [{response.status_code}]: {response.text}')
                    if not self.fail_silently:
                        response.raise_for_status()
            except Exception as e:
                logger.error(f'Failed to send email via Brevo API: {e}', exc_info=True)
                if not self.fail_silently:
                    raise

        return sent_count
