"""Платформо-независимые DTO для событий бота"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional


class ParseMode(str, Enum):
    PLAIN = 'plain'
    MARKDOWN = 'markdown'
    HTML = 'html'


class KeyboardType(str, Enum):
    INLINE = 'inline'
    REPLY = 'reply'


@dataclass
class KeyboardButton:
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Keyboard:
    buttons: List[List[KeyboardButton]] = field(default_factory=list)
    type: KeyboardType = KeyboardType.REPLY
    one_time: bool = False

    def row(self, *buttons: KeyboardButton) -> 'Keyboard':
        self.buttons.append(list(buttons))
        return self


@dataclass
class OutgoingMessage:
    chat_id: str
    text: str
    parse_mode: ParseMode = ParseMode.PLAIN
    keyboard: Optional[Keyboard] = None
    remove_keyboard: bool = False


@dataclass
class IncomingFile:
    """Файл, прикреплённый пользователем. `content` заполняется лениво."""
    file_id: str
    file_name: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    download: Optional[Callable[[], bytes]] = None

    def read(self) -> bytes:
        if self.download is None:
            raise RuntimeError('File download callback is not set')
        return self.download()


@dataclass
class IncomingEvent:
    """Единое событие от пользователя независимо от типа."""
    chat_id: str
    user_id: str
    text: Optional[str] = None
    command: Optional[str] = None
    callback_data: Optional[str] = None
    file: Optional[IncomingFile] = None
    raw: Optional[object] = None
