from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [

    path('auth_success', views.auth_success),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)