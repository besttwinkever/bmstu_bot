"""Views для страниц, связанных с ботом (OAuth-callback, календарь)."""
from __future__ import annotations

import datetime
import logging

from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer

from bot_app.models import AuthToken
from bot_app.services import CalendarService
from bot_app.services.auth import AuthService
from messaging.constants import Platform


logger = logging.getLogger(__name__)


@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer])
def auth_success(request):
    """OAuth-callback: проверяет одноразовый токен, привязывает messenger_id, шлёт меню."""
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Требуется вход через SSO.')

    token = request.query_params.get('token', '')
    if not token:
        logger.warning('auth_success without token from user=%s', request.user.username)
        return HttpResponseBadRequest('Отсутствует токен авторизации.')

    auth_token = AuthToken.objects.filter(token=token).first()
    if auth_token is None:
        logger.warning('auth_success unknown token from user=%s', request.user.username)
        return HttpResponseForbidden('Ссылка недействительна или уже использована.')

    if auth_token.is_expired():
        auth_token.delete()
        return HttpResponseBadRequest('Срок действия ссылки истёк. Запросите авторизацию в боте заново.')

    # Атомарный delete защищает от повторного использования при гонке двух запросов.
    deleted, _ = AuthToken.objects.filter(pk=auth_token.pk).delete()
    if not deleted:
        logger.warning('auth_success token race user=%s', request.user.username)
        return HttpResponseForbidden('Ссылка уже использована.')

    platform = (auth_token.platform or Platform.TELEGRAM).lower()
    messenger_id = auth_token.messenger_id
    if not messenger_id:
        logger.warning('auth_success token missing messenger_id user=%s', request.user.username)
        return HttpResponseBadRequest('Требуется идентификатор пользователя мессенджера.')

    logger.info(
        'Auth success for user=%s platform=%s messenger_id=%s',
        request.user.username, platform, messenger_id,
    )

    tg_user, _ = AuthService.link_messenger(platform, messenger_id, request.user)

    try:
        from messaging.factory import get_platform
        from messaging.handlers.menu import _build_menu
        authed = AuthService.find_by_messenger_id(platform, str(messenger_id))
        if authed is not None:
            full_name = authed.full_name or authed.tg_user.user.username
            groups_str = ', '.join(authed.groups) or 'не определены'
            platform_adapter = get_platform(platform)
            platform_adapter.reply(
                str(messenger_id),
                f'Вы успешно аутентифицировались как {full_name}.\nГруппы: {groups_str}',
            )
            platform_adapter.reply(
                str(messenger_id),
                'Выберите команду:',
                keyboard=_build_menu(authed),
            )
    except Exception:
        logger.exception('Failed to send greeting/menu after auth')

    data = {
        'status': 'ok',
        'first_name': tg_user.user.first_name,
        'last_name': tg_user.user.last_name,
        'username': tg_user.user.username,
    }
    return render(request, 'success_page.html', {'data': data})


def _resolve_messenger_id(request) -> str | None:
    return request.GET.get('uid') or request.GET.get('tgid')


def _resolve_platform(request) -> str:
    return (request.GET.get('platform') or Platform.TELEGRAM).lower()


# XXX: API ниже доверяет messenger_id, переданному в GET-параметре. В
# Telegram WebApp правильное решение — валидация подписи initData
# (HMAC-SHA256 на bot token) — но эта инфраструктура не настроена.
# Полученные через эндпойнт данные минимальны (расписание дисциплины,
# в которой состоит пользователь), но enumeration по messenger_id
# теоретически возможна. Перед production обязательно добавить
# проверку Telegram WebApp signature.


@csrf_exempt
def calendar_mini_app(request):
    messenger_id = _resolve_messenger_id(request)
    platform = _resolve_platform(request)
    user_info: dict = {}

    if messenger_id:
        user = AuthService.find_by_messenger_id(platform, messenger_id)
        if user is None:
            user_info['error'] = 'Пользователь не найден'
        else:
            user_info['fio'] = user.full_name
            user_info['group'] = ', '.join(user.groups) if user.groups else 'Нет групп'

    return render(request, 'calendar.html', {'user_info': user_info})


@csrf_exempt
def get_calendar_events(request):
    messenger_id = _resolve_messenger_id(request)
    platform = _resolve_platform(request)
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not messenger_id:
        return JsonResponse({'error': 'Требуется авторизация'}, status=401)

    user = AuthService.find_by_messenger_id(platform, messenger_id)
    if user is None:
        return JsonResponse({'error': 'Пользователь не найден'}, status=404)

    events = []
    if start_str and end_str:
        try:
            start = datetime.datetime.strptime(start_str, '%Y-%m-%d')
            end = datetime.datetime.strptime(end_str, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({'events': []})

        # USE_TZ=True → CalendarService сравнивает с aware-датами, naive
        # сейчас даст RuntimeWarning и сдвиг на TIME_ZONE-смещение.
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(start, tz)
        end = timezone.make_aware(end, tz)

        for event in CalendarService.events_between(user.oauth_user, start, end):
            events.append({
                'title': event.name,
                'description': f'Дисциплина: {event.discipline}',
                'date': event.deadline.strftime('%d.%m.%Y %H:%M'),
                'groups': ', '.join(event.groups),
                'teacher': ', '.join(event.teachers),
            })
    return JsonResponse({'events': events})
