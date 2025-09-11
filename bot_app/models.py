from django.contrib.auth.models import Group
from django.db import models
from oauth.models import OauthUser


class TgUser(models.Model):
    telegram_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    user = models.OneToOneField(OauthUser, on_delete=models.CASCADE, related_name='user')
    def __str__(self):
        return self.user.username


class Discipline(models.Model):
    teachers = models.ManyToManyField(OauthUser, related_name='disciplines')
    groups = models.ManyToManyField(Group, related_name='disciplines')
    name = models.CharField(max_length=255, unique=True, null=False)
    description = models.TextField(unique=False, null=True)

    def __str__(self):
        return f"{self.name} ({",".join(list(map(lambda f: f.name,self.groups.all())))})"


class BotCommand(models.Model):
    name = models.CharField(max_length=255, unique=True, null=False)
    applicable_groups = models.ManyToManyField(Group, null=True, blank=True)
    description = models.TextField()

