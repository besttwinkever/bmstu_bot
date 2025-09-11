import telebot
from telebot import TeleBot, types
import logging
import os
import requests
from django.core.cache import cache
import os
import django
from dotenv import load_dotenv


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bauman_event_tg_bot.settings')
django.setup()
load_dotenv()  # загружает переменные из .env
from django.contrib.auth.models import Group
from .models import BotCommand, TgUser, Discipline
from bauman_event_tg_bot.settings import TELEGRAM_BOT_TOKEN, API_URL, BACKEND_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TeleBot(TELEGRAM_BOT_TOKEN)

def require_auth(handler_func):
    """Декоратор для проверки авторизации"""
    def wrapper(msg, *args, **kwargs):
        message = msg
        if type(message) == types.CallbackQuery:
            message = message.message
        telegram_id = message.chat.id
        if not TgUser.objects.filter(telegram_id=telegram_id).exists():
            auth_url = f"{API_URL}?p=telegram_id={message.chat.id},redirect_url={BACKEND_URL}/bot-app/auth_success"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Авторизоваться", url=auth_url))
            bot.send_message(
                telegram_id,
                "❗ Вы не авторизованы. Пожалуйста, авторизуйтесь через сайт университета.",
                reply_markup=markup
            )
            return
        return handler_func(msg, *args, **kwargs)
    return wrapper


from bot_send_file.commands import *

# Установка всплывающего меню команд
def set_bot_commands():
    commands = [
        types.BotCommand("start", "Начало работы с ботом"),
        types.BotCommand("menu", "Список доступных команд"),
        types.BotCommand("whoami", "Статус пользователя"),
    ]
    bot.set_my_commands(commands)



@bot.message_handler(commands=['menu'])
@require_auth
def show_menu(message):
    sent_msg = bot.send_message(message.chat.id,
                                text="Выбор доступных команд",
                                reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.send_chat_action(message.chat.id, 'typing')
    telegram_id = message.chat.id
    user = TgUser.objects.get(telegram_id=telegram_id)
    keyboard = telebot.types.InlineKeyboardMarkup()
    for cmd in BotCommand.objects.all():
        applicable = list(map(lambda g: g.name,cmd.applicable_groups.all()))
        if any(user_g in applicable for user_g in list(map(lambda g: g.name,user.user.groups.all()))):
            keyboard.add(telebot.types.InlineKeyboardButton(text=cmd.name,
                                                            callback_data=cmd.name))

    bot.delete_message(chat_id=message.chat.id, message_id=sent_msg.message_id)
    bot.send_message(
        chat_id=message.chat.id,
        text="Выберите команду:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['start'])
def start(message):
    show_menu(message)

@bot.message_handler(commands=['whoami'])
@require_auth
def whoami(message):
    telegram_id = message.chat.id
    user = TgUser.objects.get(telegram_id=telegram_id)
    menu = []
    bot.register_for_reply_by_message_id()
    bot.send_message(telegram_id, f"Вы {user.user.get_full_name()}")
    if user.user.groups.filter(name__in=['Студент']).exists():
        bot.send_message(telegram_id, f"Вы {user.user.get_full_name()}")
    elif user.user.groups.filter(name__in=['Сотрудник']).exists():
        disciplines = Discipline.objects.filter(teachers__in=[user.user])
        if disciplines.exists():
            bot.send_message(telegram_id, f"Преподаватель: {", ".join(list(map(lambda d: str(d), disciplines)))}")
        else:
            bot.send_message(telegram_id, f"Сотрудник университета")
    elif user.user.groups.filter(name__in=['Сторонний']).exists():
        bot.send_message(telegram_id, f"Сотрудник сторонней организации")
    return menu


# Запуск бота
def start_bot():
    set_bot_commands()
    
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or os.environ.get('RUN_MAIN') == 'true':
        print("Бот запущен!")
        try:
            bot.polling(none_stop=True, skip_pending=True)
        except Exception as e:
            print(f"Ошибка в работе бота: {e}")

import atexit

def stop_bot():
    try:
        bot.stop_polling()
    except Exception as e:
        print(f"Ошибка при остановке бота: {e}")

atexit.register(stop_bot)