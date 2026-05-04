"""Адаптер VK Bots LongPoll. peer_id↔chat_id, from_id↔user_id, callback-кнопки → payload."""
from __future__ import annotations

import io
import json
import logging
from typing import Callable, Dict, List, Optional

try:
    import vk_api
    from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
    from vk_api.keyboard import VkKeyboard, VkKeyboardColor
    from vk_api.utils import get_random_id
    import requests
except ImportError:  # pragma: no cover
    vk_api = None

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


class VKAdapter(MessagingPlatform):
    platform_name = Platform.VK

    def __init__(self, token: str, group_id: int):
        if vk_api is None:
            raise RuntimeError(
                'vk_api is not installed. Add it to requirements.txt '
                'or switch BOT_PLATFORM to "telegram".'
            )
        if not token or not group_id:
            raise RuntimeError('VK_BOT_TOKEN / VK_GROUP_ID are not configured')
        self._session = vk_api.VkApi(token=token)
        self._api = self._session.get_api()
        self._longpoll = VkBotLongPoll(self._session, group_id)
        self._commands: Dict[str, EventHandler] = {}
        self._callbacks: Dict[str, EventHandler] = {}
        self._callback_prefixes: List[tuple] = []
        self._text_aliases: Dict[str, EventHandler] = {}
        self._text_handlers: List[EventHandler] = []
        self._file_handlers: List[EventHandler] = []

    # ---- исходящие ------------------------------------------------------

    def send_message(self, message: OutgoingMessage) -> None:
        kwargs = {
            'peer_id': int(message.chat_id),
            'message': self._strip_markdown(message.text)
                if message.parse_mode == ParseMode.MARKDOWN else message.text,
            'random_id': get_random_id(),
        }
        if message.keyboard:
            kwargs['keyboard'] = self._build_keyboard(message.keyboard)
        elif message.remove_keyboard:
            kwargs['keyboard'] = json.dumps({'buttons': [], 'one_time': True})
        self._api.messages.send(**kwargs)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        # VK не поддерживает Telegram-Markdown — стираем парные * и _.
        import re
        cleaned = re.sub(r'\*([^\n*]+)\*', r'\1', text or '')
        cleaned = re.sub(r'_([^\n_]+)_', r'\1', cleaned)
        return cleaned

    def send_document(
        self,
        chat_id: str,
        filename: str,
        content: bytes,
        caption: str = '',
    ) -> None:
        upload_url = self._api.docs.getMessagesUploadServer(
            type='doc', peer_id=int(chat_id)
        )['upload_url']
        resp = requests.post(upload_url, files={'file': (filename, content)}).json()
        saved = self._api.docs.save(file=resp['file'])
        attachment_id = saved['doc']['id']
        owner_id = saved['doc']['owner_id']
        self._api.messages.send(
            peer_id=int(chat_id),
            message=caption,
            attachment=f'doc{owner_id}_{attachment_id}',
            random_id=get_random_id(),
        )

    def set_commands(self, commands: list[tuple[str, str]]) -> None:
        # VK API не имеет аналога setMyCommands — команды только через /<name>.
        logger.info('VK set_commands: %s', commands)

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
        logger.info('VK bot LongPoll started')
        for event in self._longpoll.listen():
            try:
                self._dispatch(event)
            except Exception:
                logger.exception('Error dispatching VK event')

    @staticmethod
    def _parse_payload(raw) -> dict:
        """VK отдаёт payload иногда строкой JSON, иногда сразу dict."""
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    # Кнопка «Начать» шлёт payload {"command":"start"}, но при пересылке текстом
    # приходит обычное «Начать»/«Start» — ловим оба случая.
    _START_TEXTS = {'начать', 'start', '/start', 'старт'}

    def _dispatch(self, event) -> None:
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.message
            text = (msg.get('text', '') or '').strip()
            peer_id = str(msg['peer_id'])
            from_id = str(msg['from_id'])

            attachments = msg.get('attachments') or []
            doc_att = next(
                (a['doc'] for a in attachments if a.get('type') == 'doc'),
                None,
            )

            if doc_att:
                file = IncomingFile(
                    file_id=str(doc_att['id']),
                    file_name=doc_att.get('title', 'file'),
                    mime_type=doc_att.get('ext'),
                    size=doc_att.get('size'),
                    download=(lambda u=doc_att['url']: requests.get(u).content),
                )
                inc = IncomingEvent(
                    chat_id=peer_id,
                    user_id=from_id,
                    text=text,
                    file=file,
                    raw=msg,
                )
                for handler in self._file_handlers:
                    self._safe_call(handler, inc)
                return

            payload = self._parse_payload(msg.get('payload'))
            payload_command = payload.get('command') if payload else None
            if payload_command:
                handler = self._commands.get(payload_command)
                if handler:
                    self._safe_call(handler, IncomingEvent(
                        chat_id=peer_id, user_id=from_id,
                        command=payload_command, text=text, raw=msg,
                    ))
                    return

            if text.startswith('/'):
                command = text[1:].split()[0] if len(text) > 1 else ''
                handler = self._commands.get(command)
                if handler:
                    self._safe_call(handler, IncomingEvent(
                        chat_id=peer_id, user_id=from_id,
                        command=command, text=text, raw=msg,
                    ))
                    return

            if text.lower() in self._START_TEXTS:
                handler = self._commands.get('start')
                if handler:
                    self._safe_call(handler, IncomingEvent(
                        chat_id=peer_id, user_id=from_id,
                        command='start', text=text, raw=msg,
                    ))
                    return

            inc = IncomingEvent(chat_id=peer_id, user_id=from_id, text=text, raw=msg)
            alias = self._text_aliases.get(text)
            if alias is not None:
                self._safe_call(alias, inc)
                return
            for handler in self._text_handlers:
                self._safe_call(handler, inc)
            return

        if event.type == VkBotEventType.MESSAGE_EVENT:
            obj = event.object
            payload = self._parse_payload(obj.get('payload'))
            data = payload.get('callback_data') if payload else None

            # Без ack кнопка показывает «загрузку» бесконечно.
            self._answer_event(obj)

            if not data:
                return
            handler = self._callbacks.get(data)
            if handler is None:
                for prefix, prefix_handler in self._callback_prefixes:
                    if data.startswith(prefix):
                        handler = prefix_handler
                        break
            if handler is None:
                return
            self._safe_call(handler, IncomingEvent(
                chat_id=str(obj['peer_id']),
                user_id=str(obj['user_id']),
                callback_data=data,
                raw=obj,
            ))

    def _answer_event(self, obj) -> None:
        try:
            self._api.messages.sendMessageEventAnswer(
                event_id=obj['event_id'],
                user_id=obj['user_id'],
                peer_id=obj['peer_id'],
            )
        except Exception:
            logger.debug('VK sendMessageEventAnswer failed', exc_info=True)

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

    def _build_keyboard(self, kb: Keyboard) -> str:
        vk_kb = VkKeyboard(
            one_time=(kb.one_time and kb.type == KeyboardType.REPLY),
            inline=(kb.type == KeyboardType.INLINE),
        )
        for idx, row in enumerate(kb.buttons):
            if idx > 0:
                vk_kb.add_line()
            for button in row:
                if button.url:
                    vk_kb.add_openlink_button(button.text, button.url)
                elif button.callback_data is not None:
                    vk_kb.add_callback_button(
                        label=button.text,
                        color=VkKeyboardColor.PRIMARY,
                        payload={'callback_data': button.callback_data},
                    )
                else:
                    vk_kb.add_button(button.text, color=VkKeyboardColor.SECONDARY)
        return vk_kb.get_keyboard()
