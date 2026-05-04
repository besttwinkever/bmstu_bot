"""Загрузка работы: FSM-сценарий выбор дисциплины → выбор типа → файл."""
from __future__ import annotations

import logging
from typing import Optional

from bot_app.services.auth import AuthenticatedUser, AuthService
from bot_send_file.services import SubmissionNotAllowed, SubmissionService
from bot_send_file.validators import FileValidationError

from ..constants import ButtonLabel, CallbackData, FSMState
from ..contracts import Keyboard, KeyboardButton, KeyboardType
from ..dispatcher import Dispatcher
from ..fsm import fsm
from ..platform import Context


logger = logging.getLogger(__name__)


def _discipline_keyboard(user_model) -> Keyboard:
    disciplines = SubmissionService.disciplines_for(user_model)
    kb = Keyboard()
    for d in disciplines:
        kb.row(KeyboardButton(text=d.name))
    kb.row(KeyboardButton(text=ButtonLabel.CANCEL))
    return kb


def _submission_type_keyboard(discipline) -> Keyboard:
    kb = Keyboard()
    for st in SubmissionService.submittable_types(discipline):
        kb.row(KeyboardButton(text=st.name))
    kb.row(KeyboardButton(text=ButtonLabel.BACK), KeyboardButton(text=ButtonLabel.CANCEL))
    return kb


def _file_keyboard() -> Keyboard:
    kb = Keyboard()
    kb.row(KeyboardButton(text=ButtonLabel.BACK), KeyboardButton(text=ButtonLabel.CANCEL))
    return kb


def _start_upload(ctx: Context) -> None:
    user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
    if user is None:
        ctx.reply('Сначала авторизуйтесь через /start.')
        return

    disciplines = SubmissionService.disciplines_for(user.oauth_user)
    if not disciplines:
        ctx.reply('Нет доступных дисциплин', remove_keyboard=True)
        return

    fsm.set_state(ctx.platform_name, ctx.user_id, FSMState.AWAITING_DISCIPLINE)
    ctx.reply('Выберите дисциплину', keyboard=_discipline_keyboard(user.oauth_user))


def _cancel(ctx: Context) -> None:
    fsm.clear(ctx.platform_name, ctx.user_id)
    # После отмены возвращаем главное меню — иначе reply-клавиатура
    # пропадает и пользователю нужно набирать /menu.
    from .menu import _build_menu
    user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
    if user is not None:
        ctx.reply('Действие отменено.', keyboard=_build_menu(user))
    else:
        ctx.reply('Действие отменено.', remove_keyboard=True)


def _handle_text(ctx: Context) -> None:
    text = (ctx.event.text or '').strip()
    if not text:
        return

    session = fsm.get(ctx.platform_name, ctx.user_id)
    if session.state is None:
        return  # не наш сценарий

    if text == ButtonLabel.CANCEL:
        _cancel(ctx)
        return

    if session.state == FSMState.AWAITING_DISCIPLINE:
        _on_discipline(ctx, text)
    elif session.state == FSMState.AWAITING_SUBMISSION_TYPE:
        _on_submission_type(ctx, text, session.data)
    elif session.state == FSMState.AWAITING_FILE:
        _on_file_step_text(ctx, text, session.data)


def _on_discipline(ctx: Context, name: str) -> None:
    user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
    if user is None:
        _cancel(ctx)
        return

    discipline = SubmissionService.find_discipline(user.oauth_user, name)
    if discipline is None:
        ctx.reply(
            'Выбранная дисциплина недоступна. Попробуйте ещё раз или нажмите Отмена.'
        )
        return

    submission_types = SubmissionService.submittable_types(discipline)
    if not submission_types:
        ctx.reply(
            'По этой дисциплине нет открытых заданий — все сроки сдачи прошли.',
            remove_keyboard=True,
        )
        fsm.clear(ctx.platform_name, ctx.user_id)
        return

    fsm.set_state(
        ctx.platform_name, ctx.user_id,
        FSMState.AWAITING_SUBMISSION_TYPE,
        {'discipline_id': discipline.pk, 'discipline_name': discipline.name},
    )
    ctx.reply(
        f'Выберите тип работы по дисциплине {discipline.name}',
        keyboard=_submission_type_keyboard(discipline),
    )


def _on_submission_type(ctx: Context, name: str, data: dict) -> None:
    user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
    if user is None:
        _cancel(ctx)
        return

    if name == ButtonLabel.BACK:
        fsm.set_state(ctx.platform_name, ctx.user_id, FSMState.AWAITING_DISCIPLINE, {})
        ctx.reply('Выберите дисциплину', keyboard=_discipline_keyboard(user.oauth_user))
        return

    discipline = SubmissionService.find_discipline(user.oauth_user, data.get('discipline_name', ''))
    if discipline is None:
        _cancel(ctx)
        return

    submission_type = SubmissionService.find_submission_type(discipline, name)
    if submission_type is None:
        ctx.reply('Неверный тип работы. Попробуйте ещё раз.')
        return

    if SubmissionService.is_locked(submission_type):
        deadline_str = submission_type.deadline.strftime('%d.%m.%Y %H:%M')
        ctx.reply(
            f'Файл не принят: срок сдачи задания «{submission_type.name}» истёк '
            f'({deadline_str}). Это задание больше не принимает работы.',
            keyboard=_submission_type_keyboard(discipline),
        )
        return

    fsm.set_state(
        ctx.platform_name, ctx.user_id,
        FSMState.AWAITING_FILE,
        {'submission_type_id': submission_type.pk, 'submission_type_name': submission_type.name},
    )
    info_lines = [
        f'Разрешены: {submission_type.allowed_extensions}. '
        f'Макс. размер: {submission_type.max_file_size_mb} МБ.',
    ]
    if submission_type.deadline:
        deadline_str = submission_type.deadline.strftime('%d.%m.%Y %H:%M')
        if submission_type.accept_late:
            info_lines.append(
                f'Срок: {deadline_str} (после срока - принимается с пометкой «опоздание»).'
            )
        else:
            info_lines.append(f'Срок: {deadline_str}.')
    ctx.reply(
        f"Прикрепите файл для '{submission_type.name}' по дисциплине "
        f"'{discipline.name}'.\n" + '\n'.join(info_lines),
        keyboard=_file_keyboard(),
    )


def _on_file_step_text(ctx: Context, text: str, data: dict) -> None:
    user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
    if user is None:
        _cancel(ctx)
        return

    if text == ButtonLabel.BACK:
        discipline = SubmissionService.find_discipline(user.oauth_user, data.get('discipline_name', ''))
        if discipline is None:
            _cancel(ctx)
            return
        fsm.set_state(
            ctx.platform_name, ctx.user_id,
            FSMState.AWAITING_SUBMISSION_TYPE,
            {'discipline_id': discipline.pk, 'discipline_name': discipline.name},
        )
        ctx.reply(
            f'Выберите тип работы по дисциплине {discipline.name}',
            keyboard=_submission_type_keyboard(discipline),
        )
        return

    ctx.reply('Пожалуйста, прикрепите файл (документ).')


def _handle_file(ctx: Context) -> None:
    session = fsm.get(ctx.platform_name, ctx.user_id)
    if session.state != FSMState.AWAITING_FILE:
        return

    user = AuthService.find_by_messenger_id(ctx.platform_name, ctx.user_id)
    if user is None:
        _cancel(ctx)
        return

    submission_type_id: Optional[int] = session.data.get('submission_type_id')
    if submission_type_id is None:
        _cancel(ctx)
        return

    from bot_send_file.models import SubmissionType
    submission_type = SubmissionType.objects.filter(pk=submission_type_id).first()
    if submission_type is None:
        _cancel(ctx)
        return

    file = ctx.event.file
    if file is None:
        ctx.reply('Пожалуйста, прикрепите файл.')
        return

    ctx.reply('Файл загружается, пожалуйста подождите...', remove_keyboard=True)
    try:
        content = file.read()
        SubmissionService.submit(
            user=user.oauth_user,
            submission_type=submission_type,
            file_name=file.file_name,
            file_bytes=content,
            file_size=file.size,
        )
    except FileValidationError as exc:
        ctx.reply(f'Файл не принят: {exc}')
        return
    except SubmissionNotAllowed as exc:
        ctx.reply(f'Недостаточно прав: {exc}')
        return
    except Exception:
        logger.exception('File upload failed')
        ctx.reply('Ошибка при отправке файла.')
        return
    finally:
        fsm.clear(ctx.platform_name, ctx.user_id)

    from .menu import _build_menu
    ctx.reply('Файл успешно отправлен.', keyboard=_build_menu(user))


def _start_upload_via_button(ctx: Context) -> None:
    fsm.clear(ctx.platform_name, ctx.user_id)
    _start_upload(ctx)


def register(dispatcher: Dispatcher) -> None:
    dispatcher.callbacks[CallbackData.SEND_FILE] = _start_upload
    dispatcher.callbacks[ButtonLabel.SEND_FILE] = _start_upload
    dispatcher.text_aliases[ButtonLabel.SEND_FILE] = _start_upload_via_button
    dispatcher.text_handlers.append(_handle_text)
    dispatcher.file_handlers.append(_handle_file)
