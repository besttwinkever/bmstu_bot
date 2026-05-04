"""Деаутентификация: команда /logout и кнопка в меню."""
from __future__ import annotations

import logging

from bot_app.models import TgUser

from ..constants import ButtonLabel, CallbackData
from ..dispatcher import Dispatcher
from ..fsm import fsm
from ..platform import Context


logger = logging.getLogger(__name__)


def _logout(ctx: Context) -> None:
    fsm.clear(ctx.platform_name, ctx.user_id)
    deleted, _ = TgUser.objects.filter(
        platform=ctx.platform_name,
        messenger_id=str(ctx.user_id),
    ).delete()
    if deleted:
        ctx.reply(
            'Вы вышли из бота. Чтобы войти снова — наберите /start и пройдите авторизацию.',
            remove_keyboard=True,
        )
    else:
        ctx.reply('Вы и так не авторизованы.', remove_keyboard=True)


def register(dispatcher: Dispatcher) -> None:
    dispatcher.commands['logout'] = _logout
    dispatcher.callbacks[CallbackData.LOGOUT] = _logout
    dispatcher.text_aliases[ButtonLabel.LOGOUT] = _logout
