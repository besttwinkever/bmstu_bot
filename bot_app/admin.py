from django.contrib import admin
from oauth.models import OauthUser

from bot_app.models import TgUser, Discipline, BotCommand

# Register your models here.
admin.site.register(TgUser)
admin.site.register(OauthUser)
admin.site.register(Discipline)
admin.site.register(BotCommand)
