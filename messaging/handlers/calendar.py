"""Интерактивный календарь контрольных мероприятий (ТЗ 3.1.2).

Сценарий:
* `/calendar` — показывает текущую неделю с inline-кнопками навигации.
* «← пред. / след. →» — переход на соседнюю неделю в пределах 30 дней.
* Клик по конкретному событию — детальная карточка (дедлайн, преподаватель, группы).
"""
from __future__ import annotations

import datetime
import logging

from django.utils import timezone

from bot_app.services import CalendarService
from bot_app.services.auth import AuthenticatedUser
from bot_send_file.models import SubmissionType

from ..contracts import Keyboard, KeyboardButton, KeyboardType, ParseMode
from ..dispatcher import Dispatcher
from ..platform import Context
from ._auth import require_auth


logger = logging.getLogger(__name__)


CB_PREFIX = 'cal:'
CB_WEEK = 'cal:wk:'        # cal:wk:<offset>   offset — целое, 0 = текущая неделя
CB_EVENT = 'cal:evt:'      # cal:evt:<submission_type_pk>

WEEKS_AHEAD = 4   # 4 шага вперёд от текущей недели — суммарно ≈30 дней
WEEKS_BACK = 0    # назад не ходим


def _week_bounds(offset: int) -> tuple[datetime.datetime, datetime.datetime]:
    """Понедельник 00:00 ↔ следующий понедельник 00:00 в локальной TZ."""
    now = timezone.localtime()
    monday = (now - datetime.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = monday + datetime.timedelta(weeks=offset)
    end = start + datetime.timedelta(days=7)
    return start, end


_WEEKDAYS_RU = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')


def _ru_day(dt: datetime.datetime) -> str:
    return f'{_WEEKDAYS_RU[dt.weekday()]} {dt.strftime("%d.%m")}'


def _format_week(events, start: datetime.datetime, end: datetime.datetime) -> str:
    header = f'*Календарь {start.strftime("%d.%m")}–{(end - datetime.timedelta(days=1)).strftime("%d.%m.%Y")}*'
    if not events:
        return f'{header}\n\nНа этой неделе событий нет.'

    lines = [header, '']
    by_day: dict[str, list] = {}
    for ev in events:
        key = _ru_day(ev.deadline)
        by_day.setdefault(key, []).append(ev)
    for day, items in by_day.items():
        lines.append(f'*{day}*')
        for ev in items:
            lines.append(f'  • {ev.deadline.strftime("%H:%M")} — {ev.name} _({ev.discipline})_')
        lines.append('')
    return '\n'.join(lines).rstrip()


def _week_keyboard(events_with_pk, offset: int) -> Keyboard:
    rows: list[list[KeyboardButton]] = []

    # Каждое событие — отдельной кнопкой для drill-down.
    for pk, label in events_with_pk:
        rows.append([KeyboardButton(text=label, callback_data=f'{CB_EVENT}{pk}')])

    # Навигация по неделям в пределах окна.
    nav: list[KeyboardButton] = []
    if offset > WEEKS_BACK:
        nav.append(KeyboardButton(text='← Пред.', callback_data=f'{CB_WEEK}{offset - 1}'))
    if offset < WEEKS_AHEAD:
        nav.append(KeyboardButton(text='След. →', callback_data=f'{CB_WEEK}{offset + 1}'))
    if nav:
        rows.append(nav)

    return Keyboard(type=KeyboardType.INLINE, buttons=rows)


def _events_for_week(user, offset: int):
    """Возвращает (events, [(pk, label), …]) для указанной недели."""
    start, end = _week_bounds(offset)
    events = CalendarService.events_between(user.oauth_user, start, end)
    events.sort(key=lambda e: e.deadline)

    # Для drill-down нам нужны pk SubmissionType — CalendarEvent его не носит,
    # поэтому отдельно тянем минимальный список из БД, согласованный по фильтру.
    submission_types = (
        SubmissionType.objects
        .filter(
            discipline__groups__pk__in=user.oauth_user.groups.exclude(
                name__in={'Студент', 'Преподаватель', 'Сторонний'},
            ).values_list('pk', flat=True),
            deadline__gte=start,
            deadline__lt=end,
        )
        .order_by('deadline')
        .distinct()
    )
    pk_labels = [
        (st.pk, f'{st.deadline.strftime("%d.%m %H:%M")} {st.name}')
        for st in submission_types
    ]
    return events, pk_labels


def _show_week(ctx: Context, user: AuthenticatedUser, offset: int) -> None:
    offset = max(WEEKS_BACK, min(offset, WEEKS_AHEAD))
    events, pk_labels = _events_for_week(user, offset)
    start, end = _week_bounds(offset)
    ctx.reply(
        _format_week(events, start, end),
        parse_mode=ParseMode.MARKDOWN,
        keyboard=_week_keyboard(pk_labels, offset),
    )


def _show_event(ctx: Context, user: AuthenticatedUser, pk: int) -> None:
    st = (
        SubmissionType.objects
        .select_related('discipline')
        .prefetch_related('discipline__groups', 'discipline__teachers')
        .filter(pk=pk)
        .first()
    )
    if st is None or st.deadline is None:
        ctx.reply('Событие не найдено или у него нет срока сдачи.')
        return

    teachers = ', '.join(t.get_full_name() or t.username for t in st.discipline.teachers.all()) or '—'
    groups = ', '.join(g.name for g in st.discipline.groups.all()) or '—'

    text = (
        f'*{st.name}*\n'
        f'Дисциплина: {st.discipline.name}\n'
        f'Срок сдачи: {st.deadline.strftime("%d.%m.%Y %H:%M")}\n'
        f'Преподаватели: {teachers}\n'
        f'Группы: {groups}\n'
        f'Доп. приём после срока: {"да" if st.accept_late else "нет"}'
    )
    ctx.reply(text, parse_mode=ParseMode.MARKDOWN)


# ---- хэндлеры -----------------------------------------------------------

@require_auth
def _calendar(ctx: Context, user: AuthenticatedUser) -> None:
    _show_week(ctx, user, offset=0)


@require_auth
def _on_callback(ctx: Context, user: AuthenticatedUser) -> None:
    data = ctx.event.callback_data or ''
    if data.startswith(CB_WEEK):
        try:
            offset = int(data[len(CB_WEEK):])
        except ValueError:
            return
        _show_week(ctx, user, offset)
        return
    if data.startswith(CB_EVENT):
        try:
            pk = int(data[len(CB_EVENT):])
        except ValueError:
            return
        _show_event(ctx, user, pk)
        return


def _calendar_via_button(ctx: Context) -> None:
    from ..fsm import fsm
    fsm.clear(ctx.platform_name, ctx.user_id)
    _calendar(ctx)


def register(dispatcher: Dispatcher) -> None:
    from ..constants import ButtonLabel
    dispatcher.commands['calendar'] = _calendar
    dispatcher.callback_prefixes.append((CB_PREFIX, _on_callback))
    dispatcher.text_aliases[ButtonLabel.CALENDAR] = _calendar_via_button
