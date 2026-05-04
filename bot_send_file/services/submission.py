"""Сохранение и валидация загруженных работ. Антиплагиат — через post_save сигнал."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from bot_app.models import Discipline
from bot_app.services.auth import AuthService
from bot_send_file.models import Submission, SubmissionType
from bot_send_file.validators import FileValidator, FileValidationError


logger = logging.getLogger(__name__)


class SubmissionNotAllowed(Exception):
    """Пользователь не принадлежит группе, к которой привязана дисциплина."""


@dataclass
class SavedFile:
    relative_path: str
    absolute_path: str


class SubmissionService:
    @staticmethod
    def _academic_group_ids(user):
        return AuthService.academic_group_ids(user)

    @staticmethod
    def disciplines_for(user) -> list[Discipline]:
        return list(
            Discipline.objects
            .filter(groups__pk__in=SubmissionService._academic_group_ids(user))
            .distinct()
        )

    @staticmethod
    def submission_types(discipline: Discipline) -> list[SubmissionType]:
        return list(SubmissionType.objects.filter(discipline=discipline))

    @staticmethod
    def submittable_types(discipline: Discipline) -> list[SubmissionType]:
        return [
            st for st in SubmissionType.objects.filter(discipline=discipline)
            if not SubmissionService.is_locked(st)
        ]

    @staticmethod
    def is_locked(submission_type: SubmissionType) -> bool:
        return bool(
            submission_type.deadline
            and timezone.now() > submission_type.deadline
            and not submission_type.accept_late
        )

    @staticmethod
    def find_discipline(user, name: str) -> Optional[Discipline]:
        return (
            Discipline.objects
            .filter(groups__pk__in=SubmissionService._academic_group_ids(user), name=name)
            .distinct()
            .first()
        )

    @staticmethod
    def find_submission_type(discipline: Discipline, name: str) -> Optional[SubmissionType]:
        return SubmissionType.objects.filter(discipline=discipline, name=name).first()

    @classmethod
    def submit(
        cls,
        user,
        submission_type: SubmissionType,
        file_name: str,
        file_bytes: bytes,
        file_size: Optional[int] = None,
    ) -> Submission:
        if not submission_type.discipline.groups.filter(
            pk__in=SubmissionService._academic_group_ids(user)
        ).exists():
            raise SubmissionNotAllowed(
                f'Дисциплина "{submission_type.discipline.name}" '
                f'недоступна пользователю'
            )

        validator = FileValidator(submission_type)
        validator.validate(file_name, file_size if file_size is not None else len(file_bytes))

        saved = cls._save_file(user, submission_type, file_name, file_bytes)

        is_late = bool(
            submission_type.deadline
            and timezone.now() > submission_type.deadline
        )

        with transaction.atomic():
            submission = Submission.objects.create(
                submission_type=submission_type,
                user=user,
                is_late=is_late,
            )
            submission.file.name = saved.relative_path
            submission.save(update_fields=['file'])
        return submission

    @staticmethod
    def _save_file(user, submission_type: SubmissionType, file_name: str, data: bytes) -> SavedFile:
        relative_dir = os.path.join(
            'submissions',
            submission_type.discipline.name.replace(' ', '_'),
            submission_type.name.replace(' ', '_'),
            (user.get_full_name() or user.username).replace(' ', '_'),
        )
        abs_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
        os.makedirs(abs_dir, exist_ok=True)
        abs_path = os.path.join(abs_dir, file_name)
        with open(abs_path, 'wb') as fp:
            fp.write(data)
        return SavedFile(
            relative_path=os.path.join(relative_dir, file_name),
            absolute_path=abs_path,
        )
