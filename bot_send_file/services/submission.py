"""Сохранение и валидация загруженных работ. Антиплагиат — через post_save сигнал."""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from bot_app.models import Discipline
from bot_app.services.auth import AuthService
from bot_send_file.models import Submission, SubmissionType
from bot_send_file.validators import FileValidator, FileValidationError


# Имена студентов, дисциплин и приходящих файлов идут в файловую систему.
# Все символы, которыми можно сбежать из MEDIA_ROOT (или которые ОС считает
# спецсимволами), заменяем на «_». Без санитизации возможен path traversal:
# Telegram/VK позволяют отправить файл с именем «../../etc/passwd».
_UNSAFE_FS_CHARS = re.compile(r'[^\w.\-+]+', re.UNICODE)


def sanitize_path_component(value: str, fallback: str = 'file') -> str:
    value = (value or '').strip().replace('\\', '/').split('/')[-1]
    value = _UNSAFE_FS_CHARS.sub('_', value).strip('._') or fallback
    return value[:200]


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
        safe_name = sanitize_path_component(file_name, fallback='file')
        relative_dir = os.path.join(
            'submissions',
            sanitize_path_component(submission_type.discipline.name, 'discipline'),
            sanitize_path_component(submission_type.name, 'assignment'),
            sanitize_path_component(
                user.get_full_name() or user.username, fallback='user',
            ),
        )
        abs_dir = os.path.realpath(os.path.join(settings.MEDIA_ROOT, relative_dir))
        media_root = os.path.realpath(settings.MEDIA_ROOT)
        if os.path.commonpath([abs_dir, media_root]) != media_root:
            raise SubmissionNotAllowed('Недопустимый путь сохранения файла.')
        os.makedirs(abs_dir, exist_ok=True)
        abs_path = os.path.join(abs_dir, safe_name)
        with open(abs_path, 'wb') as fp:
            fp.write(data)
        return SavedFile(
            relative_path=os.path.join(relative_dir, safe_name).replace('\\', '/'),
            absolute_path=abs_path,
        )
