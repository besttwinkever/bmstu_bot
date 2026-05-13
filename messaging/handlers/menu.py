"""Главное меню: /start, /menu, постоянная reply-клавиатура."""
from __future__ import annotations

from bot_app.services.auth import AuthenticatedUser

from ..constants import ButtonLabel
from ..contracts import Keyboard, KeyboardButton, KeyboardType, ParseMode
from ..dispatcher import Dispatcher
from ..platform import Context
from ._auth import require_auth


def _build_menu(user: AuthenticatedUser) -> Keyboard:
    """Постоянное reply-меню. Кнопки шлют свой текст — text-aliases переводят в действие."""
    rows: list[list[KeyboardButton]] = []
    for label in (
        ButtonLabel.SEND_FILE,
        ButtonLabel.MY_SUBMISSIONS,
        ButtonLabel.CALENDAR,
        ButtonLabel.LOGOUT,
    ):
        rows.append([KeyboardButton(text=label)])

    return Keyboard(type=KeyboardType.REPLY, buttons=rows, one_time=False)


@require_auth
def _start(ctx: Context, user: AuthenticatedUser) -> None:
    _show_menu(ctx, user)


@require_auth
def _menu(ctx: Context, user: AuthenticatedUser) -> None:
    _show_menu(ctx, user)


def _show_menu(ctx: Context, user: AuthenticatedUser) -> None:
    ctx.reply(
        'Выберите команду:',
        parse_mode=ParseMode.PLAIN,
        keyboard=_build_menu(user),
    )


def register(dispatcher: Dispatcher) -> None:
    dispatcher.commands['start'] = _start
    dispatcher.commands['menu'] = _menu
