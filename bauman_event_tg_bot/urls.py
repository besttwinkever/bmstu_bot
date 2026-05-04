from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/teacher/', permanent=False)),
    path('bot-admin/', admin.site.urls),
    path('bot-app/', include('bot_app.urls')),
    path('bot-oauth/', include('oauth.urls')),
    path('teacher', RedirectView.as_view(url='/teacher/', permanent=False)),
    path('teacher/', include('bot_send_file.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
