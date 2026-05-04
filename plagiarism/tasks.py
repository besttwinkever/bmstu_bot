"""Celery-задача запуска антиплагиата."""
from __future__ import annotations

import logging

from celery import shared_task

from bot_send_file.models import Submission

from .service import check_submission


logger = logging.getLogger(__name__)


@shared_task(name='plagiarism.run_check')
def run_plagiarism_check(submission_pk: int) -> None:
    try:
        submission = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        logger.warning('Submission %s not found, skipping plagiarism check', submission_pk)
        return
    check_submission(submission)
