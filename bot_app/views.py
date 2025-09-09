import json

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators import csrf
from django.views.decorators.csrf import csrf_exempt
from bot_app.models import TgUser
from django.db.models import Q

from django.utils.timezone import now
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from bot_app.oauth import clear_session, get_current_user, auth_token
from rest_framework.renderers import TemplateHTMLRenderer
from telebot import TeleBot, types
from django.core.files.storage import default_storage
from bot_app.oauth import set_user_state
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import icalendar
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware, is_naive
from datetime import datetime, time, timedelta
from django.utils.timezone import get_current_timezone
from pytz import timezone as pytz_timezone
from django.views.decorators.clickjacking import xframe_options_exempt
import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = TeleBot(TOKEN)

#
# @api_view(['GET'])
# def oauth_callback(request):
#     telegram_id = request.GET.get('telegram_id', '')
#
#     user = request.user
#     if not user:
#         return Response({'message': 'User not found'}, status=400)
#
#     if telegram_id:
#         django_user, created = User.objects.get(username=user["username"])
#         login(request, django_user)
#         if created:
#             for group in user.get("groups", []):
#                 g, cr = Group.objects.get_or_create(name=group)
#                 django_user.groups.add(g)
#         url = f"/auth_success?telegram_id={telegram_id}&first_name={user.get("firstname", "")}&"
#         return redirect(url)
#     else:
#         django_user = User.objects.get(username=user["username"])
#         if django_user:
#             login(request, django_user)
#             # return redirect(redirect_url)
#         else:
#             return Response({'message': 'User not found'}, status=400)

    
@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer])
def auth_success(request):
    telegram_id = request.query_params.get('telegram_id', '')
    user, created = TgUser.objects.get_or_create(
        telegram_id=telegram_id,
        defaults = {'user': request.user}
    )
    message =  "Hello, {0}!".format(user.user.first_name)
    if telegram_id:
        bot.delete_my_commands()
        bot.send_message(telegram_id, message)

        # if "уже авторизован" not in message:
        #     set_user_state(telegram_id, "awaiting_teacher_response")
        #     markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        #     markup.add('Да', 'Нет')
        #     bot.send_message(telegram_id, "Вы преподаватель?", reply_markup=markup)

    data = {
        'status': 'ok',
        'message': message,
        'first_name': user.user.first_name,
        'last_name': user.user.last_name,
        'username': user.user.username,
    }

    return render(request, 'success_page.html', {'data': data})

#
# # Обработчик для получения списка событий для студента
# def student_events(request):
#     user_id = request.user.id
#     try:
#         student = Student.objects.get(user_id=user_id)
#         events = Event.objects.filter(groups=student.group, date__gte=now())
#
#         events_data = [
#             {
#                 "title": event.title,
#                 "description": event.description,
#                 "date": event.date
#             } for event in events
#         ]
#         return JsonResponse({"events": events_data})
#     except Student.DoesNotExist:
#         return JsonResponse({"error": "Student not found"}, status=404)
#
# #
# @csrf_exempt
# def calendar_mini_app(request):
#     telegram_id = request.GET.get('tgid')
#     user_info = {}
#
#     if telegram_id:
#         try:
#             user = User.objects.get(telegram_id=telegram_id)
#             user_info['fio'] = f"{user.last_name} {user.first_name} {user.middle_name}"
#             if hasattr(user, 'student') and user.student.group:
#                 user_info['group'] = user.student.group.name
#             elif hasattr(user, 'teacher'):
#                 user_info['group'] = None
#         except User.DoesNotExist:
#             user_info['error'] = 'Пользователь не найден'
#
#     return render(request, 'calendar.html', {'user_info': user_info})
#
# @csrf_exempt
# def get_calendar_events(request):
#     """API для получения событий с Telegram-авторизацией"""
#     telegram_id = request.GET.get('tgid')
#     start = request.GET.get('start')
#     end = request.GET.get('end')
#
#     if not telegram_id:
#         return JsonResponse({'error': 'Требуется авторизация'}, status=401)
#
#     try:
#         user = User.objects.get(telegram_id=telegram_id)
#     except User.DoesNotExist:
#         return JsonResponse({'error': 'Пользователь не найден'}, status=404)
#
#     query = Q()
#
#     if start and end:
#         try:
#             start_date = timezone.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
#             end_date = timezone.datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
#             query &= Q(date__date__gte=start_date.date(), date__date__lte=end_date.date())
#         except Exception as e:
#             return JsonResponse({'error': f'Неверный формат дат: {e}'}, status=400)
#     else:
#         return JsonResponse({'error': 'Укажите start и end'}, status=400)
#
#     if hasattr(user, 'student') and user.student.group:
#         query &= Q(groups=user.student.group)
#     elif hasattr(user, 'teacher'):
#         query &= Q(teacher=user.teacher)
#     else:
#         return JsonResponse({'error': 'Неопределенный тип пользователя'}, status=403)
#
#     events = Event.objects.filter(query).order_by('date')
#     msk = pytz_timezone("Europe/Moscow")
#     events_data = [{
#         'title': e.title,
#         'description': e.description,
#         'date': e.date.astimezone(msk).strftime('%d.%m.%Y %H:%M'),
#         'recurrence': get_recurrence_info(e),
#         'teacher': f"{e.teacher.user.last_name} {e.teacher.user.first_name} {e.teacher.user.middle_name}".strip() if e.teacher else '',
#         'groups': [g.name for g in e.groups.all()]
#     } for e in events]
#
#     return JsonResponse({'events': events_data})
#
# @csrf_exempt
# def export_ics(request):
#     telegram_id = request.GET.get('tgid')
#     start = request.GET.get('start')
#     end = request.GET.get('end')
#     print(f"Запрос с {start} по {end}")
#     if not telegram_id or not start or not end:
#         return JsonResponse({'error': 'Нужны tgid, start и end'}, status=400)
#
#     try:
#         user = User.objects.get(telegram_id=telegram_id)
#     except User.DoesNotExist:
#         return JsonResponse({'error': 'Пользователь не найден'}, status=404)
#
#     try:
#         msk = pytz_timezone("Europe/Moscow")
#
#         # Преобразуем строки в МСК datetime
#         start_msk = msk.localize(datetime.combine(parse_date(start), time.min))
#         end_msk = msk.localize(datetime.combine(parse_date(end), time.min))
#
#         # Переводим в UTC
#         start_utc = start_msk.astimezone(timezone.utc)
#         end_utc = end_msk.astimezone(timezone.utc)
#
#     except Exception as e:
#         return JsonResponse({'error': f'Ошибка разбора дат: {e}'}, status=400)
#
#     query = Q(date__gte=start_utc, date__lt=end_utc)
#
#     if hasattr(user, 'student') and user.student.group:
#         query &= Q(groups=user.student.group)
#     elif hasattr(user, 'teacher'):
#         query &= Q(teacher=user.teacher)
#     else:
#         return JsonResponse({'error': 'Неопределенный тип пользователя'}, status=403)
#
#     print(f"Фильтрация по UTC: {start_utc} - {end_utc}")
#
#     events = Event.objects.filter(query).order_by('date')
#
#     cal = icalendar.Calendar()
#     cal.add('prodid', '-//TelegramBot Calendar Export//')
#     cal.add('version', '2.0')
#     cal.add('X-WR-TIMEZONE', 'Europe/Moscow')  # ⏱️
#
#     for event in events:
#         ev = icalendar.Event()
#         ev.add('summary', event.title)
#         ev.add('description', event.description)
#
#         # Перевод в МСК для отображения
#         start_dt = event.date.astimezone(msk)
#         end_dt = (event.date + timedelta(hours=1)).astimezone(msk)
#
#         ev.add('dtstart', start_dt)
#         ev.add('dtend', end_dt)
#         ev.add('dtstamp', timezone.now().astimezone(msk))
#         ev.add('uid', f'{event.id}@telegram-bot.local')
#         cal.add_component(ev)
#
#     response = HttpResponse(cal.to_ical(), content_type='text/calendar')
#     response['Content-Disposition'] = 'attachment; filename="events.ics"'
#     return response
#
# @xframe_options_exempt
# def select_date_webapp(request):
#     return render(request, 'select_date.html')