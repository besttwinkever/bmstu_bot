"""Реестр хэндлеров: команды, callback'и, text-aliases, файлы. Цепляется к адаптеру."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from .platform import Context, EventHandler, MessagingPlatform


@dataclass
class Dispatcher:
    platform: MessagingPlatform
    commands: Dict[str, EventHandler] = field(default_factory=dict)
    callbacks: Dict[str, EventHandler] = field(default_factory=dict)
    callback_prefixes: List[tuple] = field(default_factory=list)
    text_handlers: List[EventHandler] = field(default_factory=list)
    text_aliases: Dict[str, EventHandler] = field(default_factory=dict)
    file_handlers: List[EventHandler] = field(default_factory=list)

    def command(self, name: str) -> Callable[[EventHandler], EventHandler]:
        def decorator(func: EventHandler) -> EventHandler:
            self.commands[name] = func
            return func
        return decorator

    def callback(self, data: str) -> Callable[[EventHandler], EventHandler]:
        def decorator(func: EventHandler) -> EventHandler:
            self.callbacks[data] = func
            return func
        return decorator

    def callback_prefix(self, prefix: str) -> Callable[[EventHandler], EventHandler]:
        def decorator(func: EventHandler) -> EventHandler:
            self.callback_prefixes.append((prefix, func))
            return func
        return decorator

    def text(self, func: EventHandler) -> EventHandler:
        self.text_handlers.append(func)
        return func

    def file(self, func: EventHandler) -> EventHandler:
        self.file_handlers.append(func)
        return func

    def bind(self) -> None:
        for cmd, handler in self.commands.items():
            self.platform.on_command(cmd, handler)
        for data, handler in self.callbacks.items():
            self.platform.on_callback(data, handler)
        for prefix, handler in self.callback_prefixes:
            self.platform.on_callback_prefix(prefix, handler)
        for label, handler in self.text_aliases.items():
            self.platform.on_text_alias(label, handler)
        for handler in self.text_handlers:
            self.platform.on_text(handler)
        for handler in self.file_handlers:
            self.platform.on_file(handler)
