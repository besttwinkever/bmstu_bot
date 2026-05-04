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

    PlagiarismReport.objects.get_or_create(
        submission=instance,
        defaults={'verdict': Verdict.PENDING},
    )

    def _enqueue():
        try:
            run_plagiarism_check.delay(instance.pk)
        except Exception:
            logger.exception('Failed to enqueue plagiarism check; running inline')
            run_plagiarism_check(instance.pk)

    transaction.on_commit(_enqueue)
