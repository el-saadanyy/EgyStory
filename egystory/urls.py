from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from . import views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('cases/', include('campaigns.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin-panel/', include('administration.urls')),
    path('chatbot/', include('chatbot.urls')),
    # Serve media files in production demo when DEBUG=False
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

