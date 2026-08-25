from django.test import TestCase
from decimal import Decimal
from accounts.models import User
from campaigns.models import Campaign, Donation, CampaignStatus, CaseType
from datetime import timedelta
from django.utils import timezone

class CampaignUrgencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser2@egystory.com',
            password='TestUser@2026',
            first_name='Test',
            last_name='User'
        )

    def test_basic_urgency_score(self):
        # Campaign with no deadline, 0 raised
        c = Campaign.objects.create(
            title='Test 1',
            story='Story',
            target_amount=10000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        # Urgency: no deadline = 0 for F1 & F3. Progress 0% = 5 for F2.
        self.assertEqual(c.get_urgency_score(), 5)

    def test_progress_urgency(self):
        # Campaign with 50% progress
        c = Campaign.objects.create(
            title='Test 2',
            story='Story',
            target_amount=10000,
            owner=self.user,
            status=CampaignStatus.ACTIVE,
            raised_amount=5000
        )
        # F1=0, F2 (50%) = 15, F3=0
        score = c.get_urgency_score()
        self.assertEqual(score, 15)

    def test_deadline_urgency(self):
        # Campaign with 10 days left
        c = Campaign.objects.create(
            title='Test 3',
            story='Story',
            target_amount=10000,
            owner=self.user,
            status=CampaignStatus.ACTIVE,
            deadline=timezone.now().date() + timedelta(days=10)
        )
        # F1 (<=30) = 30. 
        # F2 (0%) = 5.
        # F3 (rate: 10000 / 10 = 1000 daily -> 10% >= 5%) = 30.
        # Total = 65.
        score = c.get_urgency_score()
        self.assertEqual(score, 65)

    def test_is_critical(self):
        # Campaign with 5 days left and 80% funded
        c = Campaign.objects.create(
            title='Test 4',
            story='Story',
            target_amount=10000,
            owner=self.user,
            status=CampaignStatus.ACTIVE,
            raised_amount=8000,
            deadline=timezone.now().date() + timedelta(days=5)
        )
        # F1 (<=7) = 40. F2 (80%) = 25. F3 (2000 / 5 = 400 -> 4%) = 20. Total = 85.
        # Threshold is 70.
        self.assertTrue(c.is_auto_critical())
        self.assertTrue(c.is_critical())

    def test_manual_critical_override(self):
        # Campaign with low urgency score (no deadline, 0 raised) -> score is 10 (< 70)
        c = Campaign.objects.create(
            title='Low Score Campaign',
            story='Story',
            target_amount=100000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        self.assertFalse(c.is_auto_critical())
        self.assertFalse(c.is_critical())

        # Enable manual override
        c.is_manual_critical = True
        c.save()
        self.assertFalse(c.is_auto_critical())
        self.assertTrue(c.is_critical())

        # Disable manual override -> returns to automatic critical evaluation
        c.is_manual_critical = False
        c.save()
        self.assertFalse(c.is_critical())

class DonationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser2@egystory.com',
            password='TestUser@2026',
            first_name='Test',
            last_name='User'
        )
        self.campaign = Campaign.objects.create(
            title='Test Campaign',
            story='Story',
            target_amount=1000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )

    def test_donation_updates_campaign_total(self):
        self.assertEqual(self.campaign.raised_amount, Decimal('0.00'))
        
        Donation.objects.create(
            campaign=self.campaign,
            donor_name='Donor 1',
            amount=200
        )
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.raised_amount, Decimal('200.00'))

    def test_donation_completes_campaign(self):
        Donation.objects.create(
            campaign=self.campaign,
            donor_name='Donor 2',
            amount=1000
        )
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.raised_amount, Decimal('1000.00'))
        self.assertEqual(self.campaign.status, CampaignStatus.COMPLETED)

class InitialAmountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser_initial@egystory.com',
            password='pwd',
            first_name='Test',
            last_name='User'
        )

    def test_campaign_creation_with_zero_initial(self):
        c = Campaign.objects.create(
            title='Zero Initial',
            story='Story',
            target_amount=1000,
            owner=self.user,
            initial_raised_amount=0
        )
        self.assertEqual(c.initial_raised_amount, Decimal('0.00'))
        self.assertEqual(c.get_progress_percentage(), 0)
        self.assertEqual(c.get_remaining_amount(), Decimal('1000.00'))

    def test_campaign_creation_with_positive_initial(self):
        c = Campaign.objects.create(
            title='Positive Initial',
            story='Story',
            target_amount=1000,
            owner=self.user,
            initial_raised_amount=400
        )
        self.assertEqual(c.initial_raised_amount, Decimal('400.00'))
        self.assertEqual(c.get_progress_percentage(), 40)
        self.assertEqual(c.get_remaining_amount(), Decimal('600.00'))
        
    def test_initial_amount_exceeding_target_rejected_in_form(self):
        from campaigns.forms import CampaignForm
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Assuming CampaignForm takes data
        img = SimpleUploadedFile(name='test_image.jpg', content=b'', content_type='image/jpeg')
        data = {
            'title': 'Bad Initial',
            'story': 'Story',
            'target_amount': '1000',
            'initial_raised_amount': '1500',
            'case_type': CaseType.NORMAL
        }
        files = {'campaign_image': img}
        form = CampaignForm(data=data, files=files)
        self.assertFalse(form.is_valid())
        self.assertIn('initial_raised_amount', form.errors)


class CategoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='catuser@egystory.com',
            password='TestUser@2026',
            first_name='Category',
            last_name='Tester'
        )
        from campaigns.models import Category
        self.medical = Category.objects.create(name='Medical')
        self.education = Category.objects.create(name='Education')

    def test_category_creation_and_slugify(self):
        self.assertEqual(self.medical.slug, 'medical')
        self.assertEqual(str(self.medical), 'Medical')

    def test_campaign_with_and_without_category(self):
        # Campaign with category
        c1 = Campaign.objects.create(
            title='Medical Campaign',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.medical,
            status=CampaignStatus.ACTIVE
        )
        self.assertEqual(c1.category.name, 'Medical')

        # Campaign without category (NULL category remains valid)
        c2 = Campaign.objects.create(
            title='Uncategorized Campaign',
            story='Story',
            target_amount=5000,
            owner=self.user,
            category=None,
            status=CampaignStatus.ACTIVE
        )
        self.assertIsNone(c2.category)

    def test_category_filtering_in_case_list(self):
        from django.test import Client
        from django.urls import reverse
        c = Client()

        Campaign.objects.create(
            title='Medical Case',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.medical,
            status=CampaignStatus.ACTIVE
        )

        response = c.get(reverse('campaigns:case_list') + '?category=medical')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medical Case')


class MultiplePicturesTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@egystory.com',
            password='TestUser@2026',
            first_name='Owner',
            last_name='User',
            is_active=True
        )
        self.other_user = User.objects.create_user(
            email='other@egystory.com',
            password='TestUser@2026',
            first_name='Other',
            last_name='User',
            is_active=True
        )
        self.staff_user = User.objects.create_user(
            email='staff@egystory.com',
            password='TestUser@2026',
            first_name='Staff',
            last_name='User',
            is_staff=True,
            is_active=True
        )

    def test_multiple_images_associated_with_campaign(self):
        from campaigns.models import CampaignImage
        from django.core.files.uploadedfile import SimpleUploadedFile

        c = Campaign.objects.create(
            title='Multi Picture Campaign',
            story='Story details',
            target_amount=5000,
            owner=self.owner,
            status=CampaignStatus.ACTIVE
        )
        
        img1 = SimpleUploadedFile("pic1.jpg", b"file_content_1", content_type="image/jpeg")
        img2 = SimpleUploadedFile("pic2.jpg", b"file_content_2", content_type="image/jpeg")

        pic1 = CampaignImage.objects.create(campaign=c, image=img1)
        pic2 = CampaignImage.objects.create(campaign=c, image=img2)

        self.assertEqual(c.images.count(), 2)
        self.assertIn(pic1, c.images.all())
        self.assertIn(pic2, c.images.all())
        self.assertEqual(str(pic1), f"Image for {c.title}")

    def test_campaign_without_additional_images(self):
        c = Campaign.objects.create(
            title='Single Picture Campaign',
            story='Story details',
            target_amount=3000,
            owner=self.owner,
            status=CampaignStatus.ACTIVE
        )
        self.assertEqual(c.images.count(), 0)

    def test_multiple_images_upload_via_case_create(self):
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.owner)
        
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )

        main_img = SimpleUploadedFile("main.gif", small_gif, content_type="image/gif")
        extra_img1 = SimpleUploadedFile("extra1.gif", small_gif, content_type="image/gif")
        extra_img2 = SimpleUploadedFile("extra2.gif", small_gif, content_type="image/gif")

        data = {
            'title': 'New Multi Image Campaign',
            'story': 'Full story description.',
            'target_amount': '10000',
            'case_type': CaseType.NORMAL,
            'campaign_image': main_img,
            'images': [extra_img1, extra_img2]
        }

        response = self.client.post(reverse('campaigns:case_create'), data=data)
        self.assertEqual(response.status_code, 302)

        campaign = Campaign.objects.get(title='New Multi Image Campaign')
        self.assertTrue(campaign.campaign_image)
        self.assertEqual(campaign.images.count(), 2)

    def test_image_deletion_authorization(self):
        from campaigns.models import CampaignImage
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile

        c = Campaign.objects.create(
            title='Delete Pic Test',
            story='Story details',
            target_amount=5000,
            owner=self.owner,
            status=CampaignStatus.ACTIVE
        )
        img = SimpleUploadedFile("pic.jpg", b"content", content_type="image/jpeg")
        pic = CampaignImage.objects.create(campaign=c, image=img)

        url = reverse('campaigns:delete_campaign_image', kwargs={'image_id': pic.id})

        # Unauthorized user (not logged in) -> redirect to login
        self.client.logout()
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Non-owner non-staff logged in user -> 403 Forbidden
        self.client.force_login(self.other_user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(CampaignImage.objects.filter(id=pic.id).exists())

        # Owner logged in -> successfully deleted
        self.client.force_login(self.owner)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CampaignImage.objects.filter(id=pic.id).exists())


from campaigns.models import Tag


class MultipleTagsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='taguser@example.com',
            password='TestPassword123',
            first_name='Tag',
            last_name='User',
            is_active=True
        )
        self.tag_medical = Tag.objects.create(name='Medical')
        self.tag_urgent = Tag.objects.create(name='Urgent')
        self.tag_education = Tag.objects.create(name='Education')

    def test_tag_creation_and_slugification(self):
        tag = Tag.objects.create(name='Emergency Relief')
        self.assertEqual(tag.name, 'Emergency Relief')
        self.assertEqual(tag.slug, 'emergency-relief')
        self.assertEqual(str(tag), 'Emergency Relief')

    def test_campaign_can_have_multiple_tags(self):
        c = Campaign.objects.create(
            title='Tagged Campaign',
            story='Story description',
            target_amount=5000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        c.tags.add(self.tag_medical, self.tag_urgent)
        self.assertEqual(c.tags.count(), 2)
        self.assertIn(self.tag_medical, c.tags.all())
        self.assertIn(self.tag_urgent, c.tags.all())

    def test_campaign_can_exist_with_zero_tags(self):
        c = Campaign.objects.create(
            title='No Tags Campaign',
            story='Story description',
            target_amount=3000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        self.assertEqual(c.tags.count(), 0)

    def test_multiple_tags_assignment_via_case_create(self):
        from django.urls import reverse
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.user)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        main_img = SimpleUploadedFile("main.gif", small_gif, content_type="image/gif")

        data = {
            'title': 'New Form Tagged Campaign',
            'story': 'Full story description.',
            'target_amount': '10000',
            'case_type': CaseType.NORMAL,
            'campaign_image': main_img,
            'tags': [self.tag_medical.id, self.tag_education.id]
        }

        response = self.client.post(reverse('campaigns:case_create'), data=data)
        self.assertEqual(response.status_code, 302)

        campaign = Campaign.objects.get(title='New Form Tagged Campaign')
        self.assertEqual(campaign.tags.count(), 2)
        self.assertIn(self.tag_medical, campaign.tags.all())
        self.assertIn(self.tag_education, campaign.tags.all())

    def test_tags_displayed_on_case_detail(self):
        from django.urls import reverse

        c = Campaign.objects.create(
            title='Detail View Tag Campaign',
            story='Story description',
            target_amount=5000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        c.tags.add(self.tag_medical)

        response = self.client.get(reverse('campaigns:case_detail', kwargs={'campaign_id': c.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medical')

    def test_search_by_title_and_by_tag(self):
        from django.urls import reverse

        c1 = Campaign.objects.create(
            title='Unique Title Alpha',
            story='First story description',
            target_amount=5000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        c1.tags.add(self.tag_medical)

        c2 = Campaign.objects.create(
            title='Other Campaign Beta',
            story='Second story description',
            target_amount=8000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )
        c2.tags.add(self.tag_education)

        url = reverse('campaigns:case_list')

        # 1. Search by title
        res_title = self.client.get(f"{url}?q=Unique+Title")
        self.assertEqual(res_title.status_code, 200)
        self.assertIn(c1, res_title.context['campaigns'])
        self.assertNotIn(c2, res_title.context['campaigns'])

        # 2. Search by tag
        res_tag = self.client.get(f"{url}?q=Medical")
        self.assertEqual(res_tag.status_code, 200)
        self.assertIn(c1, res_tag.context['campaigns'])
        self.assertNotIn(c2, res_tag.context['campaigns'])

        # 3. Search non-matching tag
        res_none = self.client.get(f"{url}?q=NonExistentTag")
        self.assertEqual(res_none.status_code, 200)
        self.assertNotIn(c1, res_none.context['campaigns'])
        self.assertNotIn(c2, res_none.context['campaigns'])


from campaigns.models import CampaignRating


class ProjectRatingTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='rater1@egystory.com',
            password='TestUser@2026',
            first_name='Rater',
            last_name='One',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='rater2@egystory.com',
            password='TestUser@2026',
            first_name='Rater',
            last_name='Two',
            is_active=True
        )
        self.campaign = Campaign.objects.create(
            title='Rating Test Campaign',
            story='Story details',
            target_amount=5000,
            owner=self.user1,
            status=CampaignStatus.ACTIVE
        )

    def test_create_rating(self):
        from django.urls import reverse

        self.client.force_login(self.user1)
        url = reverse('campaigns:rate_campaign', kwargs={'campaign_id': self.campaign.id})
        
        response = self.client.post(url, {'score': 5})
        self.assertEqual(response.status_code, 302)
        
        self.assertTrue(CampaignRating.objects.filter(campaign=self.campaign, user=self.user1, score=5).exists())
        self.assertEqual(self.campaign.get_rating_count(), 1)
        self.assertEqual(self.campaign.get_average_rating(), 5.0)

    def test_update_existing_rating(self):
        from django.urls import reverse

        CampaignRating.objects.create(campaign=self.campaign, user=self.user1, score=3)
        self.assertEqual(self.campaign.get_average_rating(), 3.0)

        self.client.force_login(self.user1)
        url = reverse('campaigns:rate_campaign', kwargs={'campaign_id': self.campaign.id})
        
        response = self.client.post(url, {'score': 5})
        self.assertEqual(response.status_code, 302)
        
        # Verify rating updated, not duplicated
        self.assertEqual(CampaignRating.objects.filter(campaign=self.campaign, user=self.user1).count(), 1)
        self.assertEqual(CampaignRating.objects.get(campaign=self.campaign, user=self.user1).score, 5)
        self.assertEqual(self.campaign.get_average_rating(), 5.0)

    def test_rating_average_calculation(self):
        CampaignRating.objects.create(campaign=self.campaign, user=self.user1, score=5)
        CampaignRating.objects.create(campaign=self.campaign, user=self.user2, score=3)

        self.assertEqual(self.campaign.get_rating_count(), 2)
        self.assertEqual(self.campaign.get_average_rating(), 4.0)

    def test_rating_requires_authentication(self):
        from django.urls import reverse

        url = reverse('campaigns:rate_campaign', kwargs={'campaign_id': self.campaign.id})
        response = self.client.post(url, {'score': 4})
        
        # Redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_invalid_score_rejected(self):
        from django.urls import reverse

        self.client.force_login(self.user1)
        url = reverse('campaigns:rate_campaign', kwargs={'campaign_id': self.campaign.id})
        
        # Score > 5
        response = self.client.post(url, {'score': 10})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CampaignRating.objects.filter(campaign=self.campaign, user=self.user1).exists())


class ProjectImageSliderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='slideruser@egystory.com',
            password='TestUser@2026',
            first_name='Slider',
            last_name='User',
            is_active=True
        )
        self.campaign = Campaign.objects.create(
            title='Slider Test Campaign',
            story='Story details',
            target_amount=10000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )

    def test_case_detail_context_includes_ratings_and_slider_elements(self):
        from django.urls import reverse

        url = reverse('campaigns:case_detail', kwargs={'campaign_id': self.campaign.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('rating_data', response.context)
        self.assertContains(response, 'project-slider')


from campaigns.models import CampaignReport, ReportReason, ReportStatus


class ProjectReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reporter@egystory.com',
            password='TestUser@2026',
            first_name='Reporter',
            last_name='User',
            is_active=True
        )
        self.staff_user = User.objects.create_user(
            email='staffreport@egystory.com',
            password='TestUser@2026',
            first_name='Staff',
            last_name='User',
            is_staff=True,
            is_active=True
        )
        self.campaign = Campaign.objects.create(
            title='Reported Campaign',
            story='Story details for report testing.',
            target_amount=5000,
            owner=self.user,
            status=CampaignStatus.ACTIVE
        )

    def test_user_can_submit_campaign_report(self):
        from django.urls import reverse

        self.client.force_login(self.user)
        url = reverse('campaigns:report_campaign', kwargs={'campaign_id': self.campaign.id})

        response = self.client.post(url, {
            'reason': ReportReason.FRAUD,
            'details': 'This campaign contains misleading information.'
        })
        self.assertEqual(response.status_code, 302)

        self.assertTrue(CampaignReport.objects.filter(
            campaign=self.campaign,
            reporter=self.user,
            reason=ReportReason.FRAUD
        ).exists())

    def test_unauthenticated_user_cannot_report(self):
        from django.urls import reverse

        url = reverse('campaigns:report_campaign', kwargs={'campaign_id': self.campaign.id})
        response = self.client.post(url, {
            'reason': ReportReason.SPAM,
            'details': 'Spam content explanation.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_admin_reports_panel_and_actions(self):
        from django.urls import reverse

        report = CampaignReport.objects.create(
            campaign=self.campaign,
            reporter=self.user,
            reason=ReportReason.FRAUD,
            details='Test details for admin moderation.'
        )

        self.client.force_login(self.staff_user)
        
        # 1. Admin access reports list
        res_list = self.client.get(reverse('admin_reports'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, 'Reported Campaign')

        # 2. Admin dismisses report
        url_dismiss = reverse('admin_report_action', kwargs={'report_id': report.id, 'action': 'dismiss'})
        res_action = self.client.post(url_dismiss)
        self.assertEqual(res_action.status_code, 302)
        
        report.refresh_from_db()
        self.assertEqual(report.status, ReportStatus.DISMISSED)


class SimilarProjectsTests(TestCase):
    def setUp(self):
        from campaigns.models import Category, Tag
        self.user = User.objects.create_user(
            email='similar@egystory.com',
            password='TestPassword123',
            first_name='Similar',
            last_name='Tester',
            is_active=True
        )
        self.cat_health = Category.objects.create(name='Health')
        self.cat_education = Category.objects.create(name='Education')

        self.tag_urgent = Tag.objects.create(name='UrgentCare')
        self.tag_surgery = Tag.objects.create(name='Surgery')
        self.tag_scholarship = Tag.objects.create(name='Scholarship')

        # Target main campaign
        self.main_campaign = Campaign.objects.create(
            title='Main Health Campaign',
            story='Main story text.',
            target_amount=Decimal('50000.00'),
            owner=self.user,
            category=self.cat_health,
            status=CampaignStatus.ACTIVE
        )
        self.main_campaign.tags.add(self.tag_urgent, self.tag_surgery)

    def test_similar_campaigns_excludes_current_campaign(self):
        from campaigns.views import get_similar_campaigns
        sim = get_similar_campaigns(self.main_campaign)
        self.assertNotIn(self.main_campaign, sim)

    def test_similar_campaigns_ranks_by_category_and_tags(self):
        from campaigns.views import get_similar_campaigns
        # Campaign 1: Same category + 2 matching tags (Highest score: 10 + 10 = 20)
        c1 = Campaign.objects.create(
            title='C1 Match Both Tags & Cat',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.cat_health,
            status=CampaignStatus.ACTIVE
        )
        c1.tags.add(self.tag_urgent, self.tag_surgery)

        # Campaign 2: Same category + 1 matching tag (Score: 10 + 5 = 15)
        c2 = Campaign.objects.create(
            title='C2 Match 1 Tag & Cat',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.cat_health,
            status=CampaignStatus.ACTIVE
        )
        c2.tags.add(self.tag_urgent)

        # Campaign 3: Different category + 1 matching tag (Score: 0 + 5 = 5)
        c3 = Campaign.objects.create(
            title='C3 Match 1 Tag Only',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.cat_education,
            status=CampaignStatus.ACTIVE
        )
        c3.tags.add(self.tag_surgery)

        # Campaign 4: Different category + no matching tags (Score: 0 - excluded)
        c4 = Campaign.objects.create(
            title='C4 Unrelated',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.cat_education,
            status=CampaignStatus.ACTIVE
        )
        c4.tags.add(self.tag_scholarship)

        sim = get_similar_campaigns(self.main_campaign)
        self.assertEqual(len(sim), 3)
        self.assertEqual(sim[0], c1)
        self.assertEqual(sim[1], c2)
        self.assertEqual(sim[2], c3)
        self.assertNotIn(c4, sim)

    def test_similar_campaigns_max_4_limit(self):
        from campaigns.views import get_similar_campaigns
        for i in range(6):
            c = Campaign.objects.create(
                title=f'Same Cat Campaign {i}',
                story='Story',
                target_amount=10000,
                owner=self.user,
                category=self.cat_health,
                status=CampaignStatus.ACTIVE
            )
            c.tags.add(self.tag_urgent)

        sim = get_similar_campaigns(self.main_campaign)
        self.assertEqual(len(sim), 4)

    def test_similar_campaigns_excludes_inactive_or_cancelled(self):
        from campaigns.views import get_similar_campaigns
        c_cancelled = Campaign.objects.create(
            title='Cancelled Campaign',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.cat_health,
            status=CampaignStatus.CANCELLED
        )
        c_cancelled.tags.add(self.tag_urgent)

        sim = get_similar_campaigns(self.main_campaign)
        self.assertNotIn(c_cancelled, sim)

    def test_case_detail_context_includes_similar_campaigns(self):
        from django.urls import reverse
        c1 = Campaign.objects.create(
            title='Related Campaign',
            story='Story',
            target_amount=10000,
            owner=self.user,
            category=self.cat_health,
            status=CampaignStatus.ACTIVE
        )
        c1.tags.add(self.tag_urgent)

        url = reverse('campaigns:case_detail', args=[self.main_campaign.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('similar_campaigns', response.context)
        self.assertIn(c1, response.context['similar_campaigns'])



class CreatorCancelCampaignTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='creator@egystory.com',
            password='CreatorPassword123',
            first_name='Creator',
            last_name='User',
            is_active=True
        )
        self.other_user = User.objects.create_user(
            email='other@egystory.com',
            password='OtherPassword123',
            first_name='Other',
            last_name='User',
            is_active=True
        )
        self.staff_user = User.objects.create_superuser(
            email='admincancel@egystory.com',
            password='AdminPassword123',
            first_name='Admin',
            last_name='User',
            is_active=True
        )
        self.campaign = Campaign.objects.create(
            title='Cancel Test Campaign',
            story='Test story text.',
            target_amount=Decimal('10000.00'),
            raised_amount=Decimal('1000.00'), # 10% (< 25%)
            owner=self.owner,
            status=CampaignStatus.ACTIVE
        )


    def test_creator_can_cancel_when_raised_below_25_percent(self):
        from django.urls import reverse
        self.assertTrue(self.campaign.can_creator_cancel(self.owner))
        self.client.force_login(self.owner)
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.CANCELLED)

    def test_creator_cannot_cancel_when_raised_equals_25_percent(self):
        from django.urls import reverse
        self.campaign.raised_amount = Decimal('2500.00') # Exactly 25%
        self.campaign.save()
        
        self.assertFalse(self.campaign.can_creator_cancel(self.owner))
        self.client.force_login(self.owner)
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.ACTIVE)

    def test_creator_cannot_cancel_when_raised_above_25_percent(self):
        from django.urls import reverse
        self.campaign.raised_amount = Decimal('3000.00') # 30% (> 25%)
        self.campaign.save()
        
        self.assertFalse(self.campaign.can_creator_cancel(self.owner))
        self.client.force_login(self.owner)
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.ACTIVE)

    def test_non_owner_cannot_cancel(self):
        from django.urls import reverse
        self.assertFalse(self.campaign.can_creator_cancel(self.other_user))
        self.client.force_login(self.other_user)
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.ACTIVE)

    def test_unauthenticated_user_cannot_cancel(self):
        from django.urls import reverse
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.ACTIVE)

    def test_already_cancelled_campaign_cannot_be_cancelled_again(self):
        from django.urls import reverse
        self.campaign.status = CampaignStatus.CANCELLED
        self.campaign.save()
        
        self.assertFalse(self.campaign.can_creator_cancel(self.owner))
        self.client.force_login(self.owner)
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_completed_campaign_cannot_be_cancelled(self):
        from django.urls import reverse
        self.campaign.status = CampaignStatus.COMPLETED
        self.campaign.save()
        
        self.assertFalse(self.campaign.can_creator_cancel(self.owner))
        self.client.force_login(self.owner)
        url = reverse('campaigns:cancel_campaign', args=[self.campaign.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_existing_admin_cancellation_still_works(self):
        from django.urls import reverse
        self.client.force_login(self.staff_user)
        url = reverse('admin_campaign_action', args=[self.campaign.id, 'cancel'])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.CANCELLED)


class AlmostFundedFilterTests(TestCase):
    def setUp(self):
        from campaigns.models import Category, Donation
        self.user = User.objects.create_user(
            email='almostfunded@egystory.com',
            password='Password123',
            first_name='Almost',
            last_name='Funded',
            is_active=True
        )
        self.category = Category.objects.create(name='Relief')

        # Campaign 1: Active, 90% funded (Should appear in Almost Funded)
        self.almost_funded_campaign = Campaign.objects.create(
            title='Almost Funded Campaign',
            story='Story text',
            target_amount=Decimal('10000.00'),
            raised_amount=Decimal('9000.00'),
            owner=self.user,
            category=self.category,
            status=CampaignStatus.ACTIVE
        )

        # Campaign 2: Active, 50% funded (Should NOT appear in Almost Funded)
        self.half_funded_campaign = Campaign.objects.create(
            title='Half Funded Campaign',
            story='Story text',
            target_amount=Decimal('10000.00'),
            raised_amount=Decimal('5000.00'),
            owner=self.user,
            category=self.category,
            status=CampaignStatus.ACTIVE
        )

        # Campaign 3: Completed status, 100% funded (Should NOT appear in Almost Funded)
        self.completed_campaign = Campaign.objects.create(
            title='Completed Campaign',
            story='Story text',
            target_amount=Decimal('10000.00'),
            raised_amount=Decimal('10000.00'),
            owner=self.user,
            category=self.category,
            status=CampaignStatus.COMPLETED
        )

    def test_almost_funded_filter_includes_80_to_99_percent_active_campaigns(self):
        from django.urls import reverse
        url = reverse('campaigns:case_list') + '?filter=almost_funded'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        campaigns_in_context = response.context['campaigns']
        self.assertIn(self.almost_funded_campaign, campaigns_in_context)

    def test_almost_funded_filter_excludes_100_percent_or_completed_campaigns(self):
        from django.urls import reverse
        url = reverse('campaigns:case_list') + '?filter=almost_funded'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        campaigns_in_context = response.context['campaigns']
        self.assertNotIn(self.completed_campaign, campaigns_in_context)
        self.assertNotIn(self.half_funded_campaign, campaigns_in_context)

    def test_donation_reaching_target_auto_completes_and_removes_from_almost_funded(self):
        from django.urls import reverse
        from campaigns.models import Donation
        # Donate remaining 1000 EGP to push almost_funded_campaign to 100%
        Donation.objects.create(
            campaign=self.almost_funded_campaign,
            donor_name='Helper',
            donor_email='helper@egystory.com',
            amount=Decimal('1000.00')
        )
        self.almost_funded_campaign.refresh_from_db()
        # Campaign automatically transitions to COMPLETED status
        self.assertEqual(self.almost_funded_campaign.status, CampaignStatus.COMPLETED)

        # Verify it no longer appears under Almost Funded filter
        url = reverse('campaigns:case_list') + '?filter=almost_funded'
        response = self.client.get(url)
        campaigns_in_context = response.context['campaigns']
        self.assertNotIn(self.almost_funded_campaign, campaigns_in_context)

    def test_unrelated_filters_continue_working(self):
        from django.urls import reverse
        url_completed = reverse('campaigns:case_list') + '?filter=completed'
        response_completed = self.client.get(url_completed)
        self.assertIn(self.completed_campaign, response_completed.context['campaigns'])
        self.assertNotIn(self.almost_funded_campaign, response_completed.context['campaigns'])







