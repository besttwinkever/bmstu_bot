"""Фабрика адаптера мессенджера. Импорт SDK ленивый — не тянем неиспользуемые."""
from __future__ import annotations

from django.conf import settings

from .constants import Platform
from .platform import MessagingPlatform


def get_platform(platform_name: str | None = None) -> MessagingPlatform:
    name = (platform_name or getattr(settings, 'BOT_PLATFORM', Platform.TELEGRAM)).lower()

    if name == Platform.TELEGRAM:
        from .adapters.telegram import TelegramAdapter
        return TelegramAdapter(token=settings.TELEGRAM_BOT_TOKEN)

    if name == Platform.VK:
        from .adapters.vk import VKAdapter
        return VKAdapter(
            token=settings.VK_BOT_TOKEN,
            group_id=settings.VK_GROUP_ID,
        )

    raise ValueError(
        f'Unknown BOT_PLATFORM={name!r}. '
        f'Expected one of: {Platform.TELEGRAM}, {Platform.VK}'
    )
