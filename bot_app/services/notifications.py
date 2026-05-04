"""Рассылка уведомлений студентам через бот-платформу."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.utils import timezone

from bot_app.models import Discipline, Notification, TgUser
from messaging.constants import Platform
from messaging.contracts import ParseMode
from messaging.factory import get_platform
from messaging.platform import MessagingPlatform


logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    total: int
    sent: int
    failed: int


class NotificationService:
    def __init__(self, platform: Optional[MessagingPlatform] = None):
        self._platform = platform
        self._platforms: dict[str, MessagingPlatform] = {}
        if platform is not None:
            self._platforms[platform.platform_name] = platform

    @property
    def platform(self) -> MessagingPlatform:
        if self._platform is None:
            self._platform = get_platform()
        return self._platform

    def _get_platform(self, platform_name: str) -> MessagingPlatform:
        platform_name = (platform_name or Platform.TELEGRAM).lower()
        if platform_name not in self._platforms:
            self._platforms[platform_name] = get_platform(platform_name)
        return self._platforms[platform_name]

    def notify_user(self, tg_user: TgUser, text: str) -> bool:
        chat_id = tg_user.messenger_id
        if not chat_id:
            return False
        try:
            platform_name = (tg_user.platform or Platform.TELEGRAM).lower()
            platform = self._get_platform(platform_name)
            platform.reply(
                chat_id=chat_id,
                text=self._render(text, platform_name),
                parse_mode=self._parse_mode_for(platform_name),
            )
            return True
        except Exception:
            logger.exception('Failed to notify user %s', chat_id)
            return False

    def broadcast(self, discipline: Discipline, text: str) -> BroadcastResult:
        recipients = TgUser.objects.filter(
            user__groups__in=discipline.groups.all()
        ).distinct()
        message = self._format(discipline, text)

        sent = failed = 0
        for recipient in recipients:
            chat_id = recipient.messenger_id
            if not chat_id:
                continue
            try:
                platform_name = (recipient.platform or Platform.TELEGRAM).lower()
                platform = self._get_platform(platform_name)
                platform.reply(
                    chat_id,
                    self._render(message, platform_name),
                    parse_mode=self._parse_mode_for(platform_name),
                )
                sent += 1
            except Exception:
                logger.exception('Broadcast failed for %s', chat_id)
                failed += 1
        return BroadcastResult(total=sent + failed, sent=sent, failed=failed)

    def send_pending(self) -> int:
        now = timezone.now()
        pending = Notification.objects.filter(is_sent=False, scheduled_at__lte=now)
        processed = 0
        for notification in pending:
            result = self.broadcast(notification.discipline, notification.text)
            notification.is_sent = True
            notification.save(update_fields=['is_sent'])
            processed += result.sent
        return processed

    def schedule_or_send(
        self,
        discipline: Discipline,
        text: str,
        scheduled_at: Optional[datetime],
    ) -> Notification:
        immediate = scheduled_at is None
        notification = Notification.objects.create(
            discipline=discipline,
            text=text,
            scheduled_at=scheduled_at,
            is_sent=immediate,
        )
        if immediate:
            self.broadcast(discipline, text)
        return notification

    @staticmethod
    def _format(discipline: Discipline, text: str) -> str:
        return f'*Уведомление по дисциплине {discipline.name}*\n\n{text}'

    @staticmethod
    def _parse_mode_for(platform_name: str) -> ParseMode:
        return ParseMode.PLAIN if platform_name == Platform.VK else ParseMode.MARKDOWN

    @staticmethod
    def _render(text: str, platform_name: str) -> str:
        if platform_name != Platform.VK:
            return text
        # VK не поддерживает Telegram-Markdown — стираем парные * и _.
        
        cleaned = re.sub(r'\*([^\n*]+)\*', r'\1', text)
        cleaned = re.sub(r'_([^\n_]+)_', r'\1', cleaned)
        return cleaned
