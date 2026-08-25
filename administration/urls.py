from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path('campaigns/moderation/', views.campaign_moderation, name='admin_moderation'),
    path('campaign/<int:campaign_id>/edit/', views.admin_campaign_edit, name='admin_campaign_edit'),

    path('campaign/<int:campaign_id>/toggle-critical/', views.toggle_manual_critical, name='admin_toggle_manual_critical'),
    path('campaign/<int:campaign_id>/<str:action>/', views.campaign_action, name='admin_campaign_action'),
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('users/', views.user_management, name='admin_users'),
    path('users/<int:user_id>/delete/', views.delete_user, name='admin_delete_user'),
    path('admins/', views.admin_management, name='admin_management'),
    path('admins/create/', views.admin_create, name='admin_create'),
    path('admins/<int:admin_id>/edit/', views.admin_edit, name='admin_edit'),
    path('admins/<int:admin_id>/toggle-status/', views.admin_toggle_status, name='admin_toggle_status'),
    path('admins/<int:admin_id>/reset-password/', views.admin_reset_password, name='admin_reset_password'),
    path('admins/<int:admin_id>/delete/', views.admin_delete, name='admin_delete'),
    path('tags/', views.tag_management, name='admin_tags'),
    path('tags/<int:tag_id>/edit/', views.edit_tag, name='admin_edit_tag'),
    path('tags/<int:tag_id>/delete/', views.delete_tag, name='admin_delete_tag'),
    path('reports/', views.admin_reports, name='admin_reports'),
    path('reports/<int:report_id>/<str:action>/', views.admin_report_action, name='admin_report_action'),
]



