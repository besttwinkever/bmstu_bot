"""Debug-команды для разработки: смена личности и сброс привязки.

Активируются только при DEBUG=True — в проде регистрация молча отвалится.
Использование:
    /su <username>   — привязать текущий messenger_id к OauthUser с этим username.
    /whoami_debug    — показать, к кому сейчас привязан messenger_id.

Без аргумента /su предложит список доступных юзеров.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from bot_app.models import TgUser

from ..dispatcher import Dispatcher
from ..platform import Context


logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    return bool(getattr(settings, 'DEBUG', False))


def _su(ctx: Context) -> None:
    if not _is_enabled():
        ctx.reply('Команда доступна только в DEBUG-режиме.')
        return

    raw = (ctx.event.text or '').strip()
    parts = raw.split(maxsplit=1)
    target_username = parts[1].strip() if len(parts) > 1 else ''

    User = get_user_model()
    if not target_username:
        usernames = list(User.objects.order_by('username').values_list('username', flat=True)[:30])
        listing = '\n'.join(f'• {u}' for u in usernames) if usernames else '— список пуст —'
        ctx.reply(
            'Использование: /su <username>\n\n'
            f'Доступные пользователи (до 30):\n{listing}'
        )
        return

    target = User.objects.filter(username=target_username).first()
    if target is None:
        ctx.reply(f'Пользователь "{target_username}" не найден.')
        return

    platform = ctx.platform_name
    messenger_id = str(ctx.user_id)

    # Снимаем существующие привязки и для этого messenger_id, и для этого
    # OauthUser, чтобы не нарваться на UNIQUE-ограничения.
    TgUser.objects.filter(platform=platform, messenger_id=messenger_id).delete()
    TgUser.objects.filter(user=target).delete()
    TgUser.objects.create(
        platform=platform,
        messenger_id=messenger_id,
        user=target,
    )

    full_name = target.get_full_name() or target.username
    groups_str = ', '.join(target.groups.values_list('name', flat=True)) or 'без групп'
    ctx.reply(
        f'Готово. Этот {platform} теперь привязан к пользователю {full_name}.\n'
        f'Группы: {groups_str}.\n'
        f'Откройте /menu, чтобы продолжить от его имени.'
    )


def _whoami_debug(ctx: Context) -> None:
    if not _is_enabled():
        ctx.reply('Команда доступна только в DEBUG-режиме.')
        return

    tg_user = TgUser.objects.select_related('user').filter(
        platform=ctx.platform_name,
        messenger_id=str(ctx.user_id),
    ).first()
    if tg_user is None:
        ctx.reply('Этот мессенджер ни к кому не привязан.')
        return
    user = tg_user.user
    groups_str = ', '.join(user.groups.values_list('name', flat=True)) or 'без групп'
    ctx.reply(
        f'username={user.username}\n'
        f'ФИО: {user.get_full_name() or "—"}\n'
        f'Группы: {groups_str}'
    )


def register(dispatcher: Dispatcher) -> None:
    if not _is_enabled():
        return
    dispatcher.commands['su'] = _su
    dispatcher.commands['whoami_debug'] = _whoami_debug
