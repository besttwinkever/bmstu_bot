from django.contrib import admin
from django.utils.html import format_html

from bot_send_file.models import Submission, SubmissionType


@admin.register(SubmissionType)
class SubmissionTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'discipline', 'deadline', 'accept_late',
        'allowed_extensions', 'max_file_size_mb',
    )
    list_filter = ('discipline', 'accept_late')
    search_fields = ('name', 'discipline__name')
    list_select_related = ('discipline',)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'student_full_name',
        'assignment',
        'discipline',
        'created_at',
        'status_label',
        'is_late',
        'plagiarism_summary',
    )
    list_filter = (
        'status',
        'is_late',
        'submission_type__discipline',
        'submission_type',
    )
    search_fields = (
        'user__username', 'user__first_name', 'user__last_name',
        'submission_type__name',
        'submission_type__discipline__name',
    )
    readonly_fields = ('submission_id', 'created_at', 'updated_at', 'is_late')
    list_select_related = (
        'user', 'submission_type', 'submission_type__discipline', 'plagiarism_report',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(description='Студент', ordering='user__last_name')
    def student_full_name(self, obj: Submission) -> str:
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Работа', ordering='submission_type__name')
    def assignment(self, obj: Submission) -> str:
        return obj.submission_type.name

    @admin.display(description='Дисциплина', ordering='submission_type__discipline__name')
    def discipline(self, obj: Submission) -> str:
        return obj.submission_type.discipline.name

    @admin.display(description='Статус', ordering='status')
    def status_label(self, obj: Submission) -> str:
        return obj.get_status_display()

    @admin.display(description='Антиплагиат')
    def plagiarism_summary(self, obj: Submission) -> str:
        report = getattr(obj, 'plagiarism_report', None)
        if report is None:
            return '—'
        verdict = report.get_verdict_display()
        # Цветовая индикация — преподавателю не нужно вчитываться
        # в проценты, чтобы понять, есть ли проблема.
        color = {
            'plagiarism': '#dc3545',
            'suspicious': '#fd7e14',
            'original': '#198754',
            'pending': '#6c757d',
            'unsupported': '#6c757d',
            'error': '#fd7e14',
        }.get(report.verdict, '#6c757d')
        # format_html не понимает спецификаторы вроде :.1f (формирует
        # SafeString, а f-код у строки не работает) — форматируем число заранее.
        score_str = f'{report.final_score():.1f}%'
        if report.verdict in ('pending', 'unsupported', 'error'):
            return format_html(
                '<span style="color:{};font-weight:500">{}</span>',
                color, verdict,
            )
        return format_html(
            '<span style="color:{};font-weight:500">{}</span> · {}',
            color, verdict, score_str,
        )
