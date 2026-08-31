import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from campaigns.models import Campaign, CampaignStatus, Category, Tag
from chatbot.context_builder import build_chatbot_context, search_relevant_campaigns, get_recommended_campaigns
from chatbot.gemini_service import generate_chat_response

class ChatbotTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='donor@test.com',
            password='Password123!',
            first_name='Ali',
            last_name='Hassan',
            phone='01012345678',
            is_active=True
        )
        self.category = Category.objects.create(name='Medical Cases', slug='medical-cases')
        self.campaign = Campaign.objects.create(
            owner=self.user,
            category=self.category,
            title='Emergency Heart Surgery for Child',
            story='A child needs urgent surgery in Cairo medical center.',
            target_amount=50000,
            status=CampaignStatus.ACTIVE,
            campaign_image='campaigns/test.jpg'
        )

    def test_context_builder_searches_real_campaigns(self):
        """Context builder must find existing campaigns in the database."""
        results = search_relevant_campaigns('Surgery')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Emergency Heart Surgery for Child')
        self.assertEqual(results[0]['target_amount'], 50000.0)

    def test_context_builder_nonexistent_query(self):
        """Context builder must return empty list for queries that don't match any campaign."""
        results = search_relevant_campaigns('NonExistentCampaignXYZ123')
        self.assertEqual(len(results), 0)

    def test_context_builder_recommendations(self):
        """Context builder recommendation returns active campaigns."""
        recs = get_recommended_campaigns(limit=3)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]['id'], self.campaign.id)

    def test_empty_message_rejected(self):
        """Endpoint rejects empty or whitespace-only messages."""
        response = self.client.post(
            reverse('chatbot:send_message'),
            data=json.dumps({'message': '   ', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('empty', data['message'].lower())

    def test_oversized_message_rejected(self):
        """Endpoint rejects messages longer than 1000 characters."""
        long_msg = 'A' * 1005
        response = self.client.post(
            reverse('chatbot:send_message'),
            data=json.dumps({'message': long_msg, 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('too long', data['message'].lower())

    def test_malformed_json_rejected(self):
        """Endpoint gracefully rejects invalid JSON."""
        response = self.client.post(
            reverse('chatbot:send_message'),
            data="not a json",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')

    @patch('chatbot.views.generate_chat_response')
    def test_send_message_success_and_session_persistence(self, mock_gemini):
        """Valid message stores conversation in Django session and returns assistant response."""
        mock_gemini.return_value = ("Here is information about the heart surgery campaign.", None)

        response = self.client.post(
            reverse('chatbot:send_message'),
            data=json.dumps({'message': 'Tell me about the heart surgery'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['reply'], "Here is information about the heart surgery campaign.")

        # Check session persistence
        session = self.client.session
        history = session.get('chatbot_history', [])
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['role'], 'user')
        self.assertEqual(history[0]['text'], 'Tell me about the heart surgery')
        self.assertEqual(history[1]['role'], 'assistant')
        self.assertEqual(history[1]['text'], "Here is information about the heart surgery campaign.")

    @patch('chatbot.views.generate_chat_response')
    def test_gemini_api_failure_handled_gracefully(self, mock_gemini):
        """If Gemini API fails, safe error message is returned without leaking internals."""
        mock_gemini.return_value = (None, "Service is temporarily unavailable.")

        response = self.client.post(
            reverse('chatbot:send_message'),
            data=json.dumps({'message': 'Hello'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], "Service is temporarily unavailable.")

    def test_clear_and_get_history(self):
        """Clearing and retrieving history endpoints work properly."""
        # Set session history
        session = self.client.session
        session['chatbot_history'] = [{'role': 'user', 'text': 'Hi'}]
        session.save()

        get_res = self.client.get(reverse('chatbot:get_history'))
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(len(get_res.json()['history']), 1)

        clear_res = self.client.post(reverse('chatbot:clear_history'))
        self.assertEqual(clear_res.status_code, 200)

        get_res_after = self.client.get(reverse('chatbot:get_history'))
        self.assertEqual(len(get_res_after.json()['history']), 0)

    def test_account_deletion_context_included(self):
        """Account deletion procedures are always present in the platform overview context."""
        context = build_chatbot_context('how can i delete my acc ?')
        self.assertIn('Delete Account', context)
        self.assertIn('/delete/', context)
        self.assertIn('password', context.lower())
        self.assertIn('profile', context.lower())

    @patch('chatbot.views.generate_chat_response')
    def test_account_deletion_question_handling(self, mock_gemini):
        """Account deletion question sends proper context to Gemini and returns accurate instructions."""
        mock_gemini.return_value = (
            "To delete your EgyStory account, log in, navigate to your Profile page, click 'Delete Account' (/delete/), enter your current password for verification, check the confirmation box, and confirm deletion.",
            None
        )

        response = self.client.post(
            reverse('chatbot:send_message'),
            data=json.dumps({'message': 'how can i delete my acc ?', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('Delete Account', data['reply'])
        self.assertIn('password', data['reply'].lower())
