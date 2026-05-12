from django.urls import path

from . import views


urlpatterns = [
    path('auth_success', views.auth_success, name='bot_auth_success'),
    path('calendar/', views.calendar_mini_app, name='calendar'),
    path('api/calendar/events/', views.get_calendar_events, name='api_calendar_events'),
]
