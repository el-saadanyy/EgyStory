from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User

class UserManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Superuser
        self.superuser = User.objects.create_superuser(
            email='super@egystory.com',
            password='password123',
            first_name='Super',
            last_name='User'
        )
        
        # Staff user
        self.staff_user = User.objects.create_user(
            email='staff@egystory.com',
            password='password123',
            first_name='Staff',
            last_name='User'
        )
        self.staff_user.is_staff = True
        self.staff_user.is_active = True
        self.staff_user.save()
        
        # Protected user
        self.protected_user = User.objects.create_user(
            email='elsaadanymo5@gmail.com',
            password='password123',
            first_name='Protected',
            last_name='User'
        )
        self.protected_user.is_active = True
        self.protected_user.save()
        
        # Normal active user
        self.normal_active = User.objects.create_user(
            email='normal.active@egystory.com',
            password='password123',
            first_name='Normal',
            last_name='Active'
        )
        self.normal_active.is_active = True
        self.normal_active.save()
        
        # Normal inactive user
        self.normal_inactive = User.objects.create_user(
            email='normal.inactive@egystory.com',
            password='password123',
            first_name='Normal',
            last_name='Inactive'
        )
        self.normal_inactive.is_active = False
        self.normal_inactive.save()

    def test_unauthenticated_cannot_access_user_management(self):
        response = self.client.get(reverse('admin_users'))
        self.assertRedirects(response, reverse('admin_login'))

    def test_non_staff_cannot_access_user_management(self):
        self.client.force_login(self.normal_active)
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_user_management(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)

    def test_normal_users_appear_in_list(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'normal.active@egystory.com')
        self.assertContains(response, 'normal.inactive@egystory.com')

    def test_staff_users_do_not_appear_in_list(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'staff@egystory.com')
        self.assertNotContains(response, 'super@egystory.com')

    def test_post_deletion_successful(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_delete_user', args=[self.normal_active.id]))
        self.assertRedirects(response, reverse('admin_users'))
        self.assertFalse(User.objects.filter(email='normal.active@egystory.com').exists())

    def test_get_deletion_fails(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_delete_user', args=[self.normal_inactive.id]))
        self.assertRedirects(response, reverse('admin_users'))
        self.assertTrue(User.objects.filter(email='normal.inactive@egystory.com').exists())

    def test_staff_cannot_be_deleted(self):
        self.client.force_login(self.superuser) # Superuser trying to delete staff
        response = self.client.post(reverse('admin_delete_user', args=[self.staff_user.id]))
        self.assertRedirects(response, reverse('admin_users'))
        self.assertTrue(User.objects.filter(email='staff@egystory.com').exists())

    def test_superuser_cannot_be_deleted(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_delete_user', args=[self.superuser.id]))
        self.assertRedirects(response, reverse('admin_users'))
        self.assertTrue(User.objects.filter(email='super@egystory.com').exists())

    def test_protected_email_can_be_deleted(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_delete_user', args=[self.protected_user.id]))
        self.assertRedirects(response, reverse('admin_users'))
        self.assertFalse(User.objects.filter(email='elsaadanymo5@gmail.com').exists())


class AdminManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(email='super@egystory.com', password='pwd')
        self.staff_user = User.objects.create_user(email='staff@egystory.com', password='pwd', is_staff=True, is_active=True)
        self.normal_user = User.objects.create_user(email='normal@egystory.com', password='pwd', is_active=True)

    def test_normal_user_cannot_access(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('admin_management'))
        self.assertEqual(response.status_code, 403) # permission denied via admin_required/superuser_required

    def test_staff_cannot_access(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_management'))
        self.assertEqual(response.status_code, 403) # permission denied via superuser_required

    def test_superuser_can_access(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin_management'))
        self.assertEqual(response.status_code, 200)

    def test_superuser_create_admin(self):
        self.client.force_login(self.superuser)
        data = {
            'email': 'newadmin@egystory.com',
            'first_name': 'New',
            'last_name': 'Admin',
            'phone': '01012345678',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'is_active': True,
            'is_superuser': False,
        }
        response = self.client.post(reverse('admin_create'), data)
        self.assertRedirects(response, reverse('admin_management'))
        self.assertTrue(User.objects.filter(email='newadmin@egystory.com', is_staff=True).exists())

    def test_superuser_edit_admin(self):
        self.client.force_login(self.superuser)
        data = {
            'email': 'staff_updated@egystory.com',
            'first_name': 'Updated',
            'last_name': 'Admin',
            'phone': '01012345678',
            'is_active': True,
            'is_superuser': False,
            'password': '', # keep same
            'confirm_password': '',
        }
        response = self.client.post(reverse('admin_edit', args=[self.staff_user.id]), data)
        self.assertRedirects(response, reverse('admin_management'))
        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.email, 'staff_updated@egystory.com')
        self.assertEqual(self.staff_user.first_name, 'Updated')

    def test_superuser_toggle_status(self):
        self.client.force_login(self.superuser)
        # Initially active
        self.assertTrue(self.staff_user.is_active)
        response = self.client.post(reverse('admin_toggle_status', args=[self.staff_user.id]))
        self.assertRedirects(response, reverse('admin_management'))
        self.staff_user.refresh_from_db()
        self.assertFalse(self.staff_user.is_active)

    def test_superuser_reset_password(self):
        self.client.force_login(self.superuser)
        data = {
            'new_password': 'resetpassword123',
            'confirm_password': 'resetpassword123'
        }
        response = self.client.post(reverse('admin_reset_password', args=[self.staff_user.id]), data)
        self.assertRedirects(response, reverse('admin_management'))
        
        # Test new password works
        self.client.logout()
        login_success = self.client.login(email='staff@egystory.com', password='resetpassword123')
        self.assertTrue(login_success)

    def test_superuser_delete_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin_delete', args=[self.staff_user.id]))
        self.assertRedirects(response, reverse('admin_management'))
        self.assertFalse(User.objects.filter(email='staff@egystory.com').exists())

    def test_superuser_cannot_delete_self(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin_delete', args=[self.superuser.id]))
        self.assertRedirects(response, reverse('admin_management'))
        self.assertTrue(User.objects.filter(email='super@egystory.com').exists())
        
    def test_delete_requires_post(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin_delete', args=[self.staff_user.id]))
        self.assertRedirects(response, reverse('admin_management'))
        self.assertTrue(User.objects.filter(email='staff@egystory.com').exists())


class ManualCriticalPermissionTests(TestCase):
    def setUp(self):
        self.normal_user = User.objects.create_user(email='user@egystory.com', password='password123', first_name='User', last_name='Normal', is_active=True)
        self.staff_user = User.objects.create_user(email='staff@egystory.com', password='password123', is_staff=True, is_active=True)
        self.superuser = User.objects.create_superuser(email='super@egystory.com', password='password123')
        
        from campaigns.models import Campaign, CampaignStatus
        self.campaign = Campaign.objects.create(
            title='Test Campaign for Manual Critical',
            story='Story details',
            target_amount=50000,
            owner=self.normal_user,
            status=CampaignStatus.ACTIVE
        )

    def test_unauthenticated_cannot_toggle_manual_critical(self):
        response = self.client.post(reverse('admin_toggle_manual_critical', args=[self.campaign.id]))
        self.assertRedirects(response, '/admin-panel/login/')

    def test_normal_user_cannot_toggle_manual_critical(self):
        self.client.force_login(self.normal_user)
        response = self.client.post(reverse('admin_toggle_manual_critical', args=[self.campaign.id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_user_cannot_toggle_manual_critical(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_toggle_manual_critical', args=[self.campaign.id]))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_toggle_manual_critical(self):
        self.client.force_login(self.superuser)
        self.assertFalse(self.campaign.is_manual_critical)
        
        # Toggle ON
        response = self.client.post(reverse('admin_toggle_manual_critical', args=[self.campaign.id]))
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_manual_critical)
        self.assertTrue(self.campaign.is_critical())

        # Toggle OFF
        response = self.client.post(reverse('admin_toggle_manual_critical', args=[self.campaign.id]))
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.campaign.refresh_from_db()
        self.assertFalse(self.campaign.is_manual_critical)
        self.assertFalse(self.campaign.is_critical())

    def test_toggle_manual_critical_requires_post(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin_toggle_manual_critical', args=[self.campaign.id]))
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.campaign.refresh_from_db()
        self.assertFalse(self.campaign.is_manual_critical)


class CampaignModerationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email='staffmod@egystory.com', password='password123', is_staff=True, is_active=True)
        self.normal_user = User.objects.create_user(email='usermod@egystory.com', password='password123', is_active=True)

        from campaigns.models import Campaign, CampaignStatus
        self.pending_campaign = Campaign.objects.create(
            title='Pending Campaign For Moderation',
            story='Campaign story details.',
            target_amount=15000,
            owner=self.normal_user,
            status=CampaignStatus.PENDING
        )

    def test_unauthenticated_cannot_reject_campaign(self):
        response = self.client.post(reverse('admin_campaign_action', args=[self.pending_campaign.id, 'reject']))
        self.assertRedirects(response, '/admin-panel/login/')

    def test_non_staff_cannot_reject_campaign(self):
        self.client.force_login(self.normal_user)
        response = self.client.post(reverse('admin_campaign_action', args=[self.pending_campaign.id, 'reject']))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_reject_campaign_via_post(self):
        self.client.force_login(self.staff_user)
        from campaigns.models import CampaignStatus
        
        response = self.client.post(reverse('admin_campaign_action', args=[self.pending_campaign.id, 'reject']), follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.pending_campaign.refresh_from_db()
        self.assertEqual(self.pending_campaign.status, CampaignStatus.CANCELLED)
        
        messages_list = list(response.context['messages'])
        self.assertTrue(any(f'Campaign "{self.pending_campaign.title}" rejected.' in str(m) for m in messages_list))


from campaigns.models import Tag

class AdminTagManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email='stafftag@egystory.com', password='password123', is_staff=True, is_active=True)
        self.normal_user = User.objects.create_user(email='usertag@egystory.com', password='password123', is_active=True)
        self.tag = Tag.objects.create(name='Existing Tag')

    def test_unauthenticated_cannot_access_admin_tags(self):
        response = self.client.get(reverse('admin_tags'))
        self.assertRedirects(response, reverse('admin_login'))

    def test_non_staff_cannot_access_admin_tags(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('admin_tags'))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_tags_list(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_tags'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Existing Tag')

    def test_staff_can_create_tag(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_tags'), {'name': 'New Admin Tag'})
        self.assertRedirects(response, reverse('admin_tags'))
        self.assertTrue(Tag.objects.filter(name='New Admin Tag').exists())

    def test_staff_can_delete_tag(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_delete_tag', args=[self.tag.id]))
        self.assertRedirects(response, reverse('admin_tags'))
        self.assertFalse(Tag.objects.filter(id=self.tag.id).exists())


class AdminFeaturedCampaignTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email='stafffeat@egystory.com', password='password123', is_staff=True, is_active=True)
        self.normal_user = User.objects.create_user(email='userfeat@egystory.com', password='password123', is_active=True)
        from campaigns.models import Campaign, CampaignStatus, CaseType
        from decimal import Decimal
        self.campaign = Campaign.objects.create(
            owner=self.normal_user,
            title='Test Featured Campaign',
            story='Story text for testing featured flag',
            target_amount=Decimal('10000.00'),
            status=CampaignStatus.ACTIVE,
            case_type=CaseType.NORMAL,
            is_featured=False
        )

    def test_unauthenticated_cannot_toggle_featured(self):
        response = self.client.post(reverse('admin_toggle_featured', args=[self.campaign.id]))
        self.assertRedirects(response, reverse('admin_login'))

    def test_non_staff_cannot_toggle_featured(self):
        self.client.force_login(self.normal_user)
        response = self.client.post(reverse('admin_toggle_featured', args=[self.campaign.id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_toggle_featured_on_and_off(self):
        self.client.force_login(self.staff_user)
        
        # Toggle ON
        response = self.client.post(reverse('admin_toggle_featured', args=[self.campaign.id]), follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_featured)

        # Toggle OFF
        response = self.client.post(reverse('admin_toggle_featured', args=[self.campaign.id]), follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.campaign.refresh_from_db()
        self.assertFalse(self.campaign.is_featured)

    def test_admin_campaign_edit_updates_is_featured(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_campaign_edit', args=[self.campaign.id]), {
            'title': 'Updated Title',
            'story': 'Updated Story',
            'case_type': 'Normal',
            'status': 'Active',
            'is_featured': 'on',
        }, follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_featured)


class AdminCompletedCampaignTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email='staffcomp@egystory.com', password='password123', is_staff=True, is_active=True)
        self.normal_user = User.objects.create_user(email='usercomp@egystory.com', password='password123', is_active=True)
        from campaigns.models import Campaign, CampaignStatus, CaseType
        from decimal import Decimal

        self.completed_campaign = Campaign.objects.create(
            owner=self.normal_user,
            title='Completed Medical Case',
            story='Successfully funded story',
            target_amount=Decimal('50000.00'),
            raised_amount=Decimal('50000.00'),
            status=CampaignStatus.COMPLETED,
            case_type=CaseType.NORMAL
        )

        self.active_campaign = Campaign.objects.create(
            owner=self.normal_user,
            title='Active Ongoing Case',
            story='Currently active story',
            target_amount=Decimal('30000.00'),
            raised_amount=Decimal('10000.00'),
            status=CampaignStatus.ACTIVE,
            case_type=CaseType.NORMAL
        )

        self.pending_campaign = Campaign.objects.create(
            owner=self.normal_user,
            title='Pending Review Case',
            story='Story waiting for review',
            target_amount=Decimal('20000.00'),
            status=CampaignStatus.PENDING,
            case_type=CaseType.NORMAL
        )

    def test_unauthenticated_cannot_access_dashboard(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, reverse('admin_login'))

    def test_non_staff_cannot_access_dashboard(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_staff_dashboard_displays_completed_campaigns(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('completed_campaigns', response.context)
        self.assertContains(response, 'Completed Medical Case')
        self.assertIn(self.completed_campaign, response.context['completed_campaigns'])
        self.assertNotIn(self.active_campaign, response.context['completed_campaigns'])
        self.assertNotIn(self.pending_campaign, response.context['completed_campaigns'])

    def test_non_staff_cannot_delete_completed_campaign(self):
        self.client.force_login(self.normal_user)
        response = self.client.post(reverse('admin_delete_completed_campaign', args=[self.completed_campaign.id]))
        self.assertEqual(response.status_code, 403)
        from campaigns.models import Campaign
        self.assertTrue(Campaign.objects.filter(id=self.completed_campaign.id).exists())

    def test_get_request_does_not_delete_completed_campaign(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin_delete_completed_campaign', args=[self.completed_campaign.id]))
        self.assertRedirects(response, reverse('admin_dashboard'))
        from campaigns.models import Campaign
        self.assertTrue(Campaign.objects.filter(id=self.completed_campaign.id).exists())

    def test_staff_can_delete_completed_campaign_via_post(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('admin_delete_completed_campaign', args=[self.completed_campaign.id]), follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))
        from campaigns.models import Campaign
        self.assertFalse(Campaign.objects.filter(id=self.completed_campaign.id).exists())
        messages_list = list(response.context['messages'])
        self.assertTrue(any('permanently deleted' in str(m) for m in messages_list))

    def test_cannot_delete_non_completed_campaign_via_delete_completed_endpoint(self):
        self.client.force_login(self.staff_user)
        # Attempt to delete Active campaign
        response = self.client.post(reverse('admin_delete_completed_campaign', args=[self.active_campaign.id]), follow=True)
        self.assertRedirects(response, reverse('admin_dashboard'))
        from campaigns.models import Campaign
        self.assertTrue(Campaign.objects.filter(id=self.active_campaign.id).exists())
        messages_list = list(response.context['messages'])
        self.assertTrue(any('because it is not completed' in str(m) for m in messages_list))

        # Attempt to delete Pending campaign
        response2 = self.client.post(reverse('admin_delete_completed_campaign', args=[self.pending_campaign.id]), follow=True)
        self.assertRedirects(response2, reverse('admin_dashboard'))
        self.assertTrue(Campaign.objects.filter(id=self.pending_campaign.id).exists())





