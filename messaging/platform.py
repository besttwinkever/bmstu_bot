"""Абстрактный интерфейс платформы мессенджера."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from .contracts import IncomingEvent, Keyboard, OutgoingMessage, ParseMode

EventHandler = Callable[['Context'], None]


class MessagingPlatform(ABC):
    """Базовый адаптер мессенджера. Знает специфику платформы."""

    platform_name: str = ''

    @abstractmethod
    def send_message(self, message: OutgoingMessage) -> None: ...

    @abstractmethod
    def send_document(
        self,
        chat_id: str,
        filename: str,
        content: bytes,
        caption: str = '',
    ) -> None: ...

    @abstractmethod
    def set_commands(self, commands: list[tuple[str, str]]) -> None: ...

    @abstractmethod
    def on_command(self, command: str, handler: EventHandler) -> None: ...

    @abstractmethod
    def on_callback(self, callback_data: str, handler: EventHandler) -> None: ...

    def on_callback_prefix(self, prefix: str, handler: EventHandler) -> None:
        raise NotImplementedError

    def on_text_alias(self, label: str, handler: EventHandler) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_text(self, handler: EventHandler) -> None: ...

    @abstractmethod
    def on_file(self, handler: EventHandler) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    def reply(
        self,
        chat_id: str,
        text: str,
        parse_mode: ParseMode = ParseMode.PLAIN,
        keyboard: Optional[Keyboard] = None,
        remove_keyboard: bool = False,
    ) -> None:
        self.send_message(OutgoingMessage(
            chat_id=str(chat_id),
            text=text,
            parse_mode=parse_mode,
            keyboard=keyboard,
            remove_keyboard=remove_keyboard,
        ))


class Context:
    """Передаётся в хэндлер: обёртка над (event, platform). Общение через ctx.reply()."""

    def __init__(self, event: IncomingEvent, platform: MessagingPlatform):
        self.event = event
        self.platform = platform

    @property
    def chat_id(self) -> str:
        return self.event.chat_id

    @property
    def user_id(self) -> str:
        return self.event.user_id

    @property
    def platform_name(self) -> str:
        return self.platform.platform_name

    def reply(
        self,
        text: str,
        parse_mode: ParseMode = ParseMode.PLAIN,
        keyboard: Optional[Keyboard] = None,
        remove_keyboard: bool = False,
    ) -> None:
        self.platform.reply(
            self.chat_id, text, parse_mode, keyboard, remove_keyboard
        )
