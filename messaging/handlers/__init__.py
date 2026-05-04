"""Платформо-независимые хэндлеры бота.

Собираются в функцию `register(dispatcher)`, которая привязывает их к
конкретному адаптеру. Сама логика не знает, где она исполняется.
"""
from __future__ import annotations

from ..dispatcher import Dispatcher
from . import calendar as _calendar
from . import debug_su as _debug_su
from . import logout as _logout
from . import menu as _menu
from . import my_submissions as _my_submissions
from . import upload as _upload
from . import whoami as _whoami


def register(dispatcher: Dispatcher) -> None:
    _menu.register(dispatcher)
    _calendar.register(dispatcher)
    _whoami.register(dispatcher)
    _upload.register(dispatcher)
    _my_submissions.register(dispatcher)
    _logout.register(dispatcher)
    _debug_su.register(dispatcher)  # сам себя гасит при DEBUG=False
