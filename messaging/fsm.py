"""FSM в Django cache. Ключ — (platform, user_id) — без коллизий между TG и VK."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from django.core.cache import cache


DEFAULT_TIMEOUT = 60 * 60


def _key(platform: str, user_id: str) -> str:
    return f'fsm:{platform}:{user_id}'


@dataclass
class FSMSession:
    state: Optional[str] = None
    data: dict = field(default_factory=dict)


class FSMStorage:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def get(self, platform: str, user_id: str) -> FSMSession:
        raw = cache.get(_key(platform, user_id))
        if not raw:
            return FSMSession()
        return FSMSession(state=raw.get('state'), data=raw.get('data', {}))

    def set_state(
        self,
        platform: str,
        user_id: str,
        state: Optional[str],
        data: Optional[dict] = None,
    ) -> None:
        session = self.get(platform, user_id)
        session.state = state
        if data is not None:
            session.data.update(data)
        cache.set(
            _key(platform, user_id),
            {'state': session.state, 'data': session.data},
            self.timeout,
        )

    def update_data(self, platform: str, user_id: str, **kwargs: Any) -> None:
        session = self.get(platform, user_id)
        session.data.update(kwargs)
        cache.set(
            _key(platform, user_id),
            {'state': session.state, 'data': session.data},
            self.timeout,
        )

    def clear(self, platform: str, user_id: str) -> None:
        cache.delete(_key(platform, user_id))


fsm = FSMStorage()
