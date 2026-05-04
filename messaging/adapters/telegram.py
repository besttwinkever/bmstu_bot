"""Адаптер поверх pyTelegramBotAPI (telebot)."""
from __future__ import annotations

import io
import logging
from typing import Callable, Dict, List, Optional

import telebot
from telebot import types

from ..constants import Platform
from ..contracts import (
    IncomingEvent,
    IncomingFile,
    Keyboard,
    KeyboardType,
    OutgoingMessage,
    ParseMode,
)
from ..platform import Context, EventHandler, MessagingPlatform


logger = logging.getLogger(__name__)


_PARSE_MODE_MAP = {
    ParseMode.PLAIN: None,
    ParseMode.MARKDOWN: 'Markdown',
    ParseMode.HTML: 'HTML',
}


class TelegramAdapter(MessagingPlatform):
    platform_name = Platform.TELEGRAM

    def __init__(self, token: str):
        if not token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
        self._bot = telebot.TeleBot(token)
        self._commands: Dict[str, EventHandler] = {}
        self._callbacks: Dict[str, EventHandler] = {}
        self._callback_prefixes: List[tuple] = []
        self._text_aliases: Dict[str, EventHandler] = {}
        self._text_handlers: List[EventHandler] = []
        self._file_handlers: List[EventHandler] = []
        self._wired = False

    @property
    def raw_bot(self) -> telebot.TeleBot:
        return self._bot

    def send_message(self, message: OutgoingMessage) -> None:
        kwargs = {
            'chat_id': message.chat_id,
            'text': message.text,
            'parse_mode': _PARSE_MODE_MAP[message.parse_mode],
        }
        if message.remove_keyboard:
            kwargs['reply_markup'] = types.ReplyKeyboardRemove()
        elif message.keyboard:
            kwargs['reply_markup'] = self._build_markup(message.keyboard)
        self._bot.send_message(**kwargs)

    def send_document(
        self,
        chat_id: str,
        filename: str,
        content: bytes,
        caption: str = '',
    ) -> None:
        stream = io.BytesIO(content)
        stream.name = filename
        self._bot.send_document(chat_id, stream, caption=caption)

    def set_commands(self, commands: list[tuple[str, str]]) -> None:
        self._bot.set_my_commands([
            types.BotCommand(name, desc) for name, desc in commands
        ])

    def on_command(self, command: str, handler: EventHandler) -> None:
        self._commands[command] = handler

    def on_callback(self, data: str, handler: EventHandler) -> None:
        self._callbacks[data] = handler

    def on_callback_prefix(self, prefix: str, handler: EventHandler) -> None:
        self._callback_prefixes.append((prefix, handler))

    def on_text_alias(self, label: str, handler: EventHandler) -> None:
        self._text_aliases[label] = handler

    def on_text(self, handler: EventHandler) -> None:
        self._text_handlers.append(handler)

    def on_file(self, handler: EventHandler) -> None:
        self._file_handlers.append(handler)

    def run(self) -> None:
        self._wire_handlers()
        logger.info('Telegram bot polling started')
        # infinity_polling сам ловит сетевые ошибки (RemoteDisconnected) и переподключается.
        self._bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=20)

    def _wire_handlers(self) -> None:
        if self._wired:
            return
        self._wired = True

        bot = self._bot

        @bot.message_handler(commands=list(self._commands.keys()))
        def _dispatch_command(message: types.Message) -> None:
            command = (message.text or '').lstrip('/').split()[0].split('@')[0]
            handler = self._commands.get(command)
            if handler is None:
                return
            self._safe_call(handler, self._event_from_message(message, command=command))

        @bot.callback_query_handler(func=lambda c: True)
        def _dispatch_callback(call: types.CallbackQuery) -> None:
            handler = self._callbacks.get(call.data)
            if handler is None:
                for prefix, prefix_handler in self._callback_prefixes:
                    if call.data and call.data.startswith(prefix):
                        handler = prefix_handler
                        break
            if handler is None:
                return
            event = self._event_from_message(
                call.message,
                callback_data=call.data,
                user_override=str(call.from_user.id),
            )
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            self._safe_call(handler, event)

        @bot.message_handler(content_types=['document'])
        def _dispatch_document(message: types.Message) -> None:
            event = self._event_from_message(message, file=self._file_from_message(message))
            for handler in self._file_handlers:
                self._safe_call(handler, event)

        @bot.message_handler(func=lambda m: True, content_types=['text'])
        def _dispatch_text(message: types.Message) -> None:
            event = self._event_from_message(message)
            text = (message.text or '').strip()
            alias = self._text_aliases.get(text)
            if alias is not None:
                # Точное совпадение с reply-кнопкой — короткое замыкание, общие text-handler'ы пропускаем.
                self._safe_call(alias, event)
                return
            for handler in self._text_handlers:
                self._safe_call(handler, event)

    def _safe_call(self, handler: EventHandler, event: IncomingEvent) -> None:
        ctx = Context(event, self)
        try:
            handler(ctx)
        except Exception:
            logger.exception('Error in bot handler')
            try:
                ctx.reply('Произошла внутренняя ошибка. Попробуйте позже.')
            except Exception:
                pass

    def _event_from_message(
        self,
        message: types.Message,
        command: Optional[str] = None,
        callback_data: Optional[str] = None,
        file: Optional[IncomingFile] = None,
        user_override: Optional[str] = None,
    ) -> IncomingEvent:
        # text заполняем всегда — командам нужен полный текст для парсинга аргументов
        # (например, "/su demo_alice"). На команду срабатывает только commands-handler,
        # дублирования с text-handler'ами нет.
        return IncomingEvent(
            chat_id=str(message.chat.id),
            user_id=user_override or str(message.from_user.id if message.from_user else message.chat.id),
            text=message.text,
            command=command,
            callback_data=callback_data,
            file=file,
            raw=message,
        )

    def _file_from_message(self, message: types.Message) -> IncomingFile:
        doc = message.document
        bot = self._bot

        def download() -> bytes:
            file_info = bot.get_file(doc.file_id)
            return bot.download_file(file_info.file_path)

        return IncomingFile(
            file_id=doc.file_id,
            file_name=doc.file_name,
            mime_type=getattr(doc, 'mime_type', None),
            size=getattr(doc, 'file_size', None),
            download=download,
        )

    def _build_markup(self, kb: Keyboard):
        if kb.type == KeyboardType.INLINE:
            markup = types.InlineKeyboardMarkup()
            for row in kb.buttons:
                markup.add(*[
                    types.InlineKeyboardButton(
                        text=b.text,
                        callback_data=b.callback_data,
                        url=b.url,
                    ) for b in row
                ])
            return markup
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=kb.one_time,
        )
        for row in kb.buttons:
            markup.add(*[types.KeyboardButton(text=b.text) for b in row])
        return markup
