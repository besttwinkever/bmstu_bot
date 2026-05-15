"""Команда `/whoami` — показ роли пользователя (ТЗ 3.1.1)."""
from __future__ import annotations

from bot_app.models import Discipline
from bot_app.services.auth import AuthenticatedUser, UserRole

from ..dispatcher import Dispatcher
from ..platform import Context
from ._auth import require_auth


@require_auth
def _whoami(ctx: Context, user: AuthenticatedUser) -> None:
    ctx.reply(f'Вы {user.full_name}')

    if user.role == UserRole.STUDENT:
        ctx.reply(f'Роль: студент. Группы: {", ".join(user.groups) or "—"}')
    elif user.role == UserRole.STAFF:
        disciplines = list(Discipline.objects.filter(teachers=user.oauth_user))
        if disciplines:
            ctx.reply('Преподаватель: ' + ', '.join(str(d) for d in disciplines))
        else:
            ctx.reply('Преподаватель')
    elif user.role == UserRole.EXTERNAL:
        ctx.reply('Сотрудник сторонней организации')
    else:
        ctx.reply('Роль не определена')


def register(dispatcher: Dispatcher) -> None:
    dispatcher.commands['whoami'] = _whoami
