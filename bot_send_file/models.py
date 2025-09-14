import datetime
import uuid

from django.db import models
from oauth.models import OauthUser

from bot_app.models import Discipline


# Create your models here.
class SubmissionType(models.Model):
    class Meta:
        unique_together = (('name', 'discipline'),)
    name = models.CharField(max_length=255, null=False, blank=False)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}-{self.discipline}"


class Submission(models.Model):
    CHOICES = [
        ('none', 'На проверке'),
        ('check_passed', 'Проверено'),
        ('check_failed', 'Отклонено'),
        ('done', 'Принято'),
    ]
    submission_id = models.UUIDField(default=uuid.uuid4, unique=True, blank=False)
    file = models.FileField(max_length=1000,upload_to='submissions/', null=True, blank=False)
    submission_type = models.ForeignKey(SubmissionType, on_delete=models.CASCADE)
    user = models.ForeignKey(OauthUser, on_delete=models.CASCADE, related_name='submissions')
    status = models.CharField(max_length=20, choices=CHOICES, default='none')
    status_text = models.TextField(unique=False, null=True)
    created_at = models.DateTimeField(blank=False, default=datetime.datetime.now)
    updated_at = models.DateTimeField(blank=True, null=True)