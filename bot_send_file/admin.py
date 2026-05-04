from django.contrib import admin

from bot_send_file.models import Submission, SubmissionType


@admin.register(SubmissionType)
class SubmissionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'discipline', 'deadline', 'accept_late', 'max_file_size_mb')
    list_filter = ('discipline', 'accept_late')
    search_fields = ('name', 'discipline__name')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('submission_id', 'submission_type', 'user', 'status', 'is_late', 'created_at')
    list_filter = ('status', 'is_late', 'submission_type__discipline')
    search_fields = ('user__username', 'submission_type__name')
    readonly_fields = ('submission_id', 'created_at', 'updated_at')