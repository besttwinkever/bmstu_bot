from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    path('auth_success', views.auth_success),
    path('calendar/', views.calendar_mini_app, name='calendar'),
    path('api/calendar/events/', views.get_calendar_events, name='api_calendar_events'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
