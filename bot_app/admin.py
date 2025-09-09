from django.contrib import admin
from oauth.models import OauthUser

from bot_app.models import TgUser, Discipline

# Register your models here.
admin.site.register(TgUser)
admin.site.register(OauthUser)
admin.site.register(Discipline)
# admin.site.register(Teacher)
# admin.site.register(Event)
# admin.site.register(EventGroup)
# admin.site.register(EventResponse)