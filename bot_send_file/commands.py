import os
import tempfile

import telebot
from telebot import TeleBot

from bauman_event_tg_bot import settings
from bauman_event_tg_bot.settings import TELEGRAM_BOT_TOKEN
from bot_app.models import TgUser, Discipline
from bot_app.telegram_bot import require_auth
from bot_send_file.models import SubmissionType, Submission
from django.core.files import File as DjangoFile, File

bot = TeleBot(TELEGRAM_BOT_TOKEN)


@bot.callback_query_handler(func=lambda call: call.data == 'Отправить файл')
@require_auth
def send_file_command(call):
    message = call.message
    telegram_id = message.chat.id
    sent_msg=bot.send_message(
        text="Отправка файла по выбранной дисциплине",
        chat_id=message.chat.id,
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.send_chat_action(chat_id=message.chat.id, action='typing')
    user = TgUser.objects.get(telegram_id=telegram_id)
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for dis in Discipline.objects.all():
        applicable = list(map(lambda g: g.name, dis.groups.all()))
        if any(user_g in applicable for user_g in list(map(lambda g: g.name, user.user.groups.all()))):
            keyboard.add(telebot.types.KeyboardButton(text=dis.name))

    bot.delete_message(chat_id=telegram_id, message_id=sent_msg.message_id)
    bot.send_message(
        text="Выберите дисциплину",
        chat_id=message.chat.id,
        reply_markup=keyboard
    )

    bot.register_next_step_handler(message, handle_discipline_input, user)


def handle_discipline_input(message, user):
    telegram_id = message.chat.id
    discipline = message.text.strip()
    sent_msg = bot.send_message(
        message.chat.id,
        f"Отпавка файла по дисциплине {discipline}",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.send_chat_action(chat_id=message.chat.id, action='typing')

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for submission in SubmissionType.objects.filter(discipline__name=discipline):
            keyboard.add(telebot.types.KeyboardButton(text=submission.name))

    bot.delete_message(chat_id=telegram_id, message_id=sent_msg.message_id)
    bot.send_message(
        text="Выберите тип вложения",
        chat_id=message.chat.id,
        reply_markup=keyboard
    )

    bot.register_next_step_handler(message, handle_submission_type_input, user, discipline)



def handle_submission_type_input(message, user, discipline):
    telegram_id = message.chat.id
    submission_type = message.text.strip()
    sent_msg = bot.send_message(
        message.chat.id,
        f"Прикрепите файл {submission_type} по дисциплине {discipline}",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.send_chat_action(chat_id=message.chat.id, action='typing')
    bot.register_next_step_handler(message, process_file_step,  user, discipline, submission_type)


def process_file_step(message, user, discipline, submission_type):
    """Обработка файла"""
    telegram_id = message.chat.id

    if message.document:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        submission_dir = os.path.join(settings.MEDIA_ROOT,
                                      'submissions',
                                      discipline.replace(' ', '_'),
                                      submission_type.replace(' ', '_'),
                                      user.user.get_full_name().replace(' ', '_'))
        os.makedirs(submission_dir, exist_ok=True)
        file_path = os.path.join(submission_dir, file_name)
        try:
            with tempfile.NamedTemporaryFile(prefix='submissions') as new_file:
                new_file.write(downloaded_file)
                sub = Submission.objects.create(
                    submission_type=SubmissionType.objects.get(name=submission_type),
                    user=user.user
                )
                sub.file.save(file_path, new_file)
                bot.send_message(
                    message.chat.id,
                    "Файл отправлен",
                    reply_markup=telebot.types.ReplyKeyboardRemove()
                )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                "Ошибка при отправке файла",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            print(e)