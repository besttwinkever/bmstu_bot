from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='teacher_login', permanent=False)),
    path('login/', auth_views.LoginView.as_view(
        template_name='teacher/login.html',
        redirect_authenticated_user=True
    ), name='teacher_login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='teacher_login'
    ), name='teacher_logout'),
    
    path('panel/', views.teacher_panel, name='teacher_panel'),
    path('panel/discipline/<int:discipline_id>/', views.discipline_submissions, name='discipline_submissions'),
    path('panel/discipline/<int:discipline_id>/assignments/', views.manage_assignments, name='manage_assignments'),
    path('panel/discipline/<int:discipline_id>/notifications/', views.manage_notifications, name='manage_notifications'),
    path('panel/submission/<uuid:submission_id>/update/', views.update_submission, name='update_submission'),
    path('panel/submission/<uuid:submission_id>/download/', views.download_submission, name='download_submission'),
]
