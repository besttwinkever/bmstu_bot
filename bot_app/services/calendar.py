"""Календарь контрольных мероприятий (ТЗ 3.1.2)."""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Iterable

from django.utils import timezone

from bot_app.services.auth import AuthService
from bot_send_file.models import SubmissionType


@dataclass
class CalendarEvent:
    name: str
    discipline: str
    deadline: datetime.datetime
    groups: list[str]
    teachers: list[str]

    def short_text(self) -> str:
        return (
            f'*{self.deadline.strftime("%d.%m")} - {self.name}*\n'
            f'   Предмет: {self.discipline}\n'
            f'   Срок сдачи: {self.deadline.strftime("%d.%m.%Y %H:%M")}\n'
        )


class CalendarService:
    DEFAULT_WINDOW_DAYS = 30

    @staticmethod
    def _academic_group_ids(user):
        return AuthService.academic_group_ids(user)

    @staticmethod
    def events_for(user, days: int = DEFAULT_WINDOW_DAYS) -> list[CalendarEvent]:
        now = timezone.now()
        end = now + datetime.timedelta(days=days)
        return CalendarService._to_events(
            SubmissionType.objects
            .filter(
                discipline__groups__pk__in=CalendarService._academic_group_ids(user),
                deadline__gte=now,
                deadline__lte=end,
            )
            .select_related('discipline')
            .prefetch_related('discipline__groups', 'discipline__teachers')
            .order_by('deadline')
            .distinct()
        )

    @staticmethod
    def events_between(user, start: datetime.datetime, end: datetime.datetime) -> list[CalendarEvent]:
        return CalendarService._to_events(
            SubmissionType.objects
            .filter(
                discipline__groups__pk__in=CalendarService._academic_group_ids(user),
                deadline__range=[start, end],
            )
            .select_related('discipline')
            .prefetch_related('discipline__groups', 'discipline__teachers')
            .distinct()
        )

    @staticmethod
    def _to_events(qs: Iterable[SubmissionType]) -> list[CalendarEvent]:
        return [
            CalendarEvent(
                name=st.name,
                discipline=st.discipline.name,
                deadline=st.deadline,
                groups=[g.name for g in st.discipline.groups.all()],
                teachers=[t.get_full_name() for t in st.discipline.teachers.all()],
            )
            for st in qs
        ]
