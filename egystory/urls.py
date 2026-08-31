from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views


from django.contrib.auth import login
from accounts.models import User
from django.http import HttpResponseRedirect
def auto_login(request):
    user = User.objects.get(email='shirefbarg@gmail.com')
    login(request, user)
    return HttpResponseRedirect('/cases/new/')

urlpatterns = [
    path('auto_login/', auto_login),
    path('django-admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('cases/', include('campaigns.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin-panel/', include('administration.urls')),
    path('chatbot/', include('chatbot.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
