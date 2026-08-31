from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('message/', views.send_message, name='send_message'),
    path('clear/', views.clear_history, name='clear_history'),
    path('history/', views.get_history, name='get_history'),
]
