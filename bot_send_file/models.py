import uuid

from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone
from oauth.models import OauthUser

from bot_app.models import Discipline


DEFAULT_ALLOWED_EXTENSIONS = 'pdf,docx,doc,txt'
DEFAULT_MAX_FILE_SIZE_MB = 20


class SubmissionType(models.Model):
    class Meta:
        unique_together = (('name', 'discipline'),)
        verbose_name = 'Тип задания'
        verbose_name_plural = 'Типы заданий'

    name = models.CharField('Название', max_length=255, null=False, blank=False)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, verbose_name='Дисциплина')
    deadline = models.DateTimeField('Срок сдачи', null=True, blank=True)
    accept_late = models.BooleanField(
        'Принимать после срока сдачи',
        default=False,
        help_text='Если включено — поздние работы принимаются с пометкой «с опозданием».',
    )
    allowed_extensions = models.CharField(
        'Допустимые расширения',
        max_length=255,
        default=DEFAULT_ALLOWED_EXTENSIONS,
        help_text='Через запятую, например: pdf,docx,txt',
    )
    max_file_size_mb = models.PositiveIntegerField(
        'Макс. размер файла, МБ',
        default=DEFAULT_MAX_FILE_SIZE_MB,
    )

    def extension_list(self) -> list[str]:
        return [
            ext.strip().lower().lstrip('.')
            for ext in (self.allowed_extensions or '').split(',')
            if ext.strip()
        ]

    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    def __str__(self):
        return f'{self.name} — {self.discipline.name}'


class Submission(models.Model):
    CHOICES = [
        ('none', 'На проверке'),
        ('check_passed', 'Проверено'),
        ('check_failed', 'Отклонено'),
        ('done', 'Принято'),
    ]

    class Meta:
        verbose_name = 'Сданная работа'
        verbose_name_plural = 'Сданные работы'

    submission_id = models.UUIDField('Идентификатор', default=uuid.uuid4, unique=True, blank=False)
    file = models.FileField('Файл', max_length=1000, upload_to='submissions/', null=True, blank=False)
    submission_type = models.ForeignKey(
        SubmissionType, on_delete=models.CASCADE, verbose_name='Тип задания',
    )
    user = models.ForeignKey(
        OauthUser, on_delete=models.CASCADE, related_name='submissions', verbose_name='Студент',
    )
    status = models.CharField('Статус', max_length=20, choices=CHOICES, default='none')
    status_text = models.TextField('Комментарий преподавателя', unique=False, null=True, blank=True)
    created_at = models.DateTimeField('Дата загрузки', blank=False, default=timezone.now)
    updated_at = models.DateTimeField('Дата обновления', blank=True, null=True)
    is_late = models.BooleanField('С опозданием', default=False)

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} — {self.submission_type.name}'
