"""Автозапуск антиплагиата при создании Submission."""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from bot_send_file.models import Submission

from .models import PlagiarismReport, Verdict
from .tasks import run_plagiarism_check


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Submission)
def _enqueue_plagiarism_check(sender, instance: Submission, created: bool, **kwargs):
    if not created:
        return

    submission_pk = instance.pk

    def _enqueue() -> None:
        # Создаём PENDING-отчёт уже после коммита транзакции — иначе при
        # откате создания submission останется отчёт без работы.
        PlagiarismReport.objects.get_or_create(
            submission_id=submission_pk,
            defaults={'verdict': Verdict.PENDING},
        )
        try:
            run_plagiarism_check.delay(submission_pk)
        except Exception:
            logger.exception('Failed to enqueue plagiarism check; running inline')
            run_plagiarism_check(submission_pk)

    transaction.on_commit(_enqueue)
