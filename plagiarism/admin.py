from django.contrib import admin

from .models import PlagiarismReport


@admin.register(PlagiarismReport)
class PlagiarismReportAdmin(admin.ModelAdmin):
    list_display = (
        'submission', 'verdict', 'shingle_score', 'bert_score',
        'matched_with', 'updated_at',
    )
    list_filter = ('verdict',)
    search_fields = ('submission__submission_id', 'details')
    readonly_fields = ('created_at', 'updated_at')
