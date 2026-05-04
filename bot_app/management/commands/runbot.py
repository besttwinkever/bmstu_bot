"""Django-команда запуска бота.

`python manage.py runbot` берёт платформу из `settings.BOT_PLATFORM` —
Telegram или VK. Планировщик отложенных уведомлений запускается в том
же процессе (пока нет Redis/Celery-worker'а в окружении) в отдельном
потоке, но использует уже сервисный слой.
"""
from __future__ import annotations

import logging
import threading
import time

from django.core.management.base import BaseCommand

from bot_app.services import NotificationService
from messaging.runner import run as run_bot


logger = logging.getLogger(__name__)

SCHEDULER_INTERVAL_SEC = 60


def _scheduler_loop() -> None:
    service = NotificationService()
    logger.info('Notification scheduler thread started')
    while True:
        try:
            service.send_pending()
        except Exception:
            logger.exception('Scheduler error')
        time.sleep(SCHEDULER_INTERVAL_SEC)


class Command(BaseCommand):
    help = 'Запускает бота (платформа выбирается через settings.BOT_PLATFORM)'

    def handle(self, *args, **options):
        self.stdout.write('Starting bot...')
        threading.Thread(target=_scheduler_loop, daemon=True).start()
        try:
            run_bot()
        except Exception as exc:
            self.stderr.write(f'Bot crashed: {exc}')
            raise
