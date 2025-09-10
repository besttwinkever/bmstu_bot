from telebot import TeleBot

from bauman_event_tg_bot.settings import TELEGRAM_BOT_TOKEN
from bot_app.telegram_bot import require_auth

bot = TeleBot(TELEGRAM_BOT_TOKEN)


@bot.callback_query_handler(func=lambda call: call.data == 'Отправить файл')
def save_btn(call):
    message = call.message
    chat_id = message.chat.id
    message_id = message.message_id
    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                          text='Данные сохранены!')
