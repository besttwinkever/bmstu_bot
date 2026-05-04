"""Celery-задачи уведомлений.

Сами задачи тонкие — всё знание о платформе и БД живёт в
`NotificationService`. Это позволяет вызывать ту же логику из веб-view
без Celery (сразу) и из отложенной очереди.
"""
from __future__ import annotations

import logging

from celery import shared_task

from bot_app.services import NotificationService


logger = logging.getLogger(__name__)


@shared_task(name='bot_app.send_scheduled_notifications')
def send_scheduled_notifications() -> int:
    """Раздать все отложенные уведомления с истёкшим `scheduled_at`."""
    return NotificationService().send_pending()
