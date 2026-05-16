from django.db import models
from django.utils import timezone

from bot_send_file.models import Submission


class Verdict(models.TextChoices):
    PENDING = 'pending', 'В очереди'
    UNSUPPORTED = 'unsupported', 'Формат не поддерживается'
    ERROR = 'error', 'Ошибка проверки'
    ORIGINAL = 'original', 'Оригинал'
    SUSPICIOUS = 'suspicious', 'Подозрительно'
    PLAGIARISM = 'plagiarism', 'Плагиат'


class PlagiarismReport(models.Model):
    class Meta:
        verbose_name = 'Отчёт антиплагиата'
        verbose_name_plural = 'Отчёты антиплагиата'

    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name='plagiarism_report',
        verbose_name='Работа',
    )
    shingle_score = models.FloatField('Совпадение по шинглам, %', null=True, blank=True)
    bert_score = models.FloatField('Совпадение по BERT, %', null=True, blank=True)
    verdict = models.CharField(
        'Вердикт',
        max_length=32,
        choices=Verdict.choices,
        default=Verdict.PENDING,
    )
    matched_with = models.ForeignKey(
        Submission,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='plagiarism_matches',
        verbose_name='Совпадение с работой',
    )
    details = models.TextField('Подробности', blank=True, default='')
    created_at = models.DateTimeField('Создан', default=timezone.now)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    def final_score(self) -> float:
        scores = [s for s in (self.shingle_score, self.bert_score) if s is not None]
        return max(scores) if scores else 0.0

    @property
    def winning_method(self) -> str:
        """Какая метрика дала максимум — это и есть итоговая оценка."""
        s = self.shingle_score or 0.0
        b = self.bert_score or 0.0
        if self.shingle_score is None and self.bert_score is None:
            return ''
        return 'Шинглы' if s >= b else 'BERT'

    def __str__(self):
        return f'Антиплагиат: {self.get_verdict_display()} ({self.submission_id})'
