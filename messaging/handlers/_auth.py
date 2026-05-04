"""Хэлпер аутентификации для хэндлеров бота (ТЗ 3.1.1)."""
from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from django.conf import settings

from bot_app.models import AuthToken
from bot_app.services.auth import AuthService, AuthenticatedUser
from ..constants import ButtonLabel
from ..contracts import Keyboard, KeyboardButton, KeyboardType
from ..platform import Context


def _auth_keyboard(platform: str, messenger_id: str) -> Keyboard:
    backend_url = getattr(settings, 'BACKEND_URL', '')
    api_url = getattr(settings, 'API_URL', '')
    # Одноразовый случайный токен в БД: при первом успешном использовании
    # удаляется во view → повторно дёрнуть auth_success нельзя.
    token = AuthToken.issue(platform, messenger_id).token
    auth_url = f'{api_url}?p=token={token},redirect_url={backend_url}/bot-app/auth_success'
    return Keyboard(
        type=KeyboardType.INLINE,
        buttons=[[KeyboardButton(text=ButtonLabel.AUTHORIZE, url=auth_url)]],
    )


def require_auth(handler: Callable[[Context, AuthenticatedUser], None]):
    """Декоратор: пропускает только авторизованных пользователей."""

    @wraps(handler)
    def wrapper(ctx: Context) -> None:
        user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
        if user is None:
            ctx.reply(
                'Вы не авторизованы. Пожалуйста, авторизуйтесь через сайт университета.',
                keyboard=_auth_keyboard(ctx.platform_name, ctx.user_id),
            )
            return
        handler(ctx, user)

    return wrapper
