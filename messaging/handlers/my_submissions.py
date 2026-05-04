"""«Мои работы»: список собственных загрузок и удаление."""
from __future__ import annotations

import logging
import os

from django.conf import settings

from bot_app.services.auth import AuthenticatedUser
from bot_send_file.models import Submission

from ..constants import ButtonLabel, CallbackData
from ..contracts import Keyboard, KeyboardButton, KeyboardType
from ..dispatcher import Dispatcher
from ..fsm import fsm
from ..platform import Context
from ._auth import require_auth


logger = logging.getLogger(__name__)


# Удаление разрешено только пока работа не «приземлилась» в проверку:
# студент не должен иметь возможность стереть уличающую его сданную работу.
_DELETABLE_STATUSES = {'none'}
_DELETABLE_VERDICTS = {'pending', 'original', 'unsupported', 'error'}

_PAGE_SIZE = 5


def _can_delete(submission: Submission) -> bool:
    if submission.status not in _DELETABLE_STATUSES:
        return False
    report = getattr(submission, 'plagiarism_report', None)
    if report is not None and report.verdict not in _DELETABLE_VERDICTS:
        return False
    return True


def _show_page(ctx: Context, user: AuthenticatedUser, page: int) -> None:
    qs = (
        Submission.objects
        .filter(user=user.oauth_user)
        .select_related('submission_type', 'submission_type__discipline', 'plagiarism_report')
        .order_by('-created_at')
    )
    total = qs.count()
    if total == 0:
        ctx.reply('У вас пока нет загруженных работ.')
        return

    pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    submissions = list(qs[page * _PAGE_SIZE: (page + 1) * _PAGE_SIZE])

    lines = [f'Ваши работы (стр. {page + 1}/{pages}, всего {total}):']
    buttons: list[list[KeyboardButton]] = []
    for s in submissions:
        late = ' (с опозданием)' if s.is_late else ''
        status_label = dict(Submission.CHOICES).get(s.status, s.status)
        lines.append(
            f'• {s.submission_type.discipline.name} / {s.submission_type.name}{late}\n'
            f'  {s.created_at.strftime("%d.%m.%Y %H:%M")}, статус: {status_label}'
        )
        if _can_delete(s):
            buttons.append([KeyboardButton(
                text=f'Удалить: {s.submission_type.name}',
                callback_data=f'{CallbackData.DELETE_SUBMISSION_PREFIX}{s.pk}',
            )])

    nav: list[KeyboardButton] = []
    if page > 0:
        nav.append(KeyboardButton(
            text='← Пред.',
            callback_data=f'{CallbackData.MY_SUBMISSIONS_PAGE_PREFIX}{page - 1}',
        ))
    if page < pages - 1:
        nav.append(KeyboardButton(
            text='След. →',
            callback_data=f'{CallbackData.MY_SUBMISSIONS_PAGE_PREFIX}{page + 1}',
        ))
    if nav:
        buttons.append(nav)

    keyboard = Keyboard(type=KeyboardType.INLINE, buttons=buttons) if buttons else None
    if any(_can_delete(s) for s in submissions):
        lines.append('')
        lines.append('Удалить можно только работы, которые ещё не начал проверять преподаватель.')

    ctx.reply('\n'.join(lines), keyboard=keyboard)


@require_auth
def _list(ctx: Context, user: AuthenticatedUser) -> None:
    _show_page(ctx, user, page=0)


@require_auth
def _on_page(ctx: Context, user: AuthenticatedUser) -> None:
    data = ctx.event.callback_data or ''
    if not data.startswith(CallbackData.MY_SUBMISSIONS_PAGE_PREFIX):
        return
    try:
        page = int(data[len(CallbackData.MY_SUBMISSIONS_PAGE_PREFIX):])
    except ValueError:
        return
    _show_page(ctx, user, page=page)


@require_auth
def _delete(ctx: Context, user: AuthenticatedUser) -> None:
    data = ctx.event.callback_data or ''
    if not data.startswith(CallbackData.DELETE_SUBMISSION_PREFIX):
        return
    raw_pk = data[len(CallbackData.DELETE_SUBMISSION_PREFIX):]
    try:
        pk = int(raw_pk)
    except ValueError:
        ctx.reply('Некорректный идентификатор работы.')
        return

    submission = (
        Submission.objects
        .select_related('submission_type', 'plagiarism_report')
        .filter(pk=pk, user=user.oauth_user)
        .first()
    )
    if submission is None:
        ctx.reply('Работа не найдена или принадлежит другому пользователю.')
        return
    if not _can_delete(submission):
        ctx.reply('Эту работу удалить нельзя — она уже на проверке у преподавателя или помечена как плагиат.')
        return

    file_path = None
    if submission.file and submission.file.name:
        file_path = os.path.join(settings.MEDIA_ROOT, submission.file.name)

    submission.delete()

    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            logger.warning('Failed to remove submission file %s', file_path)

    ctx.reply('Работа удалена. Можете загрузить заново через «Отправить файл».')


def _list_via_button(ctx: Context) -> None:
    fsm.clear(ctx.platform_name, ctx.user_id)
    _list(ctx)


def register(dispatcher: Dispatcher) -> None:
    dispatcher.callbacks[CallbackData.MY_SUBMISSIONS] = _list
    dispatcher.callback_prefixes.append((CallbackData.DELETE_SUBMISSION_PREFIX, _delete))
    dispatcher.callback_prefixes.append((CallbackData.MY_SUBMISSIONS_PAGE_PREFIX, _on_page))
    dispatcher.text_aliases[ButtonLabel.MY_SUBMISSIONS] = _list_via_button
