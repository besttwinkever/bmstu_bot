from django.contrib import admin

from bot_send_file.models import SubmissionType, Submission

# Register your models here.
admin.site.register(SubmissionType)
admin.site.register(Submission)