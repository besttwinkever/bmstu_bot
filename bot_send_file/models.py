from django.db import models

# Create your models here.
class SubmissionType(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True, unique=True)

    def __str__(self):
        return f"{self.name}-{self.title}"
