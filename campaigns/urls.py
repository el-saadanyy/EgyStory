from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.case_list, name='case_list'),
    path('autocomplete/', views.campaign_autocomplete, name='campaign_autocomplete'),
    path('new/', views.case_create, name='case_create'),
    path('<int:campaign_id>/', views.case_detail, name='case_detail'),
    path('<int:campaign_id>/rate/', views.rate_campaign, name='rate_campaign'),
    path('<int:campaign_id>/report/', views.report_campaign, name='report_campaign'),
    path('<int:campaign_id>/donate/', views.donate, name='donate'),
    path('donate/', views.donate_general, name='donate_general'),
    path('<int:campaign_id>/cancel/', views.cancel_campaign, name='cancel_campaign'),
    path('image/<int:image_id>/delete/', views.delete_campaign_image, name='delete_campaign_image'),
]




