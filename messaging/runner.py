"""Инициализация бота и запуск polling.

Вызывается из management-команды `runbot`. Адаптер получается через
`factory.get_platform()` — меняется значением `settings.BOT_PLATFORM`.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from .dispatcher import Dispatcher
from .factory import get_platform
from .handlers import register as register_handlers
from .platform import MessagingPlatform


logger = logging.getLogger(__name__)

_BOT_COMMANDS = [
    ('start', 'Начало работы с ботом'),
    ('calendar', 'Календарь событий'),
    ('menu', 'Список доступных команд'),
    ('whoami', 'Статус пользователя'),
]

_RESTART_BASE_DELAY = 2
_RESTART_MAX_DELAY = 60


def build_dispatcher(platform: Optional[MessagingPlatform] = None) -> Dispatcher:
    platform = platform or get_platform()
    dispatcher = Dispatcher(platform=platform)
    register_handlers(dispatcher)
    dispatcher.bind()
    return dispatcher


def run() -> None:
    platform = get_platform()
    logger.info('Starting bot on platform: %s', platform.platform_name)
    try:
        platform.set_commands(_BOT_COMMANDS)
    except Exception:
        logger.warning('Failed to set bot commands', exc_info=True)
    build_dispatcher(platform)

    delay = _RESTART_BASE_DELAY
    while True:
        try:
            platform.run()
        except KeyboardInterrupt:
            logger.info('Bot stopped by user')
            return
        except Exception:
            logger.exception('Bot crashed, restarting in %ds…', delay)
            time.sleep(delay)
            delay = min(delay * 2, _RESTART_MAX_DELAY)
