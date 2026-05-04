"""Валидация загружаемого файла: расширение, размер, срок сдачи."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from django.utils import timezone

from .models import SubmissionType


class FileValidationError(Exception):
    pass


class ExtensionNotAllowed(FileValidationError):
    pass


class FileTooLarge(FileValidationError):
    pass


class DeadlinePassed(FileValidationError):
    pass


@dataclass
class FileValidator:
    submission_type: SubmissionType

    def validate(self, file_name: str, file_size: Optional[int]) -> None:
        self._validate_deadline()
        self._validate_extension(file_name)
        self._validate_size(file_size)

    def _validate_extension(self, file_name: str) -> None:
        ext = os.path.splitext(file_name)[1].lstrip('.').lower()
        allowed = self.submission_type.extension_list()
        if ext not in allowed:
            raise ExtensionNotAllowed(
                f'Расширение ".{ext}" не разрешено. '
                f'Допустимые: {", ".join(allowed) or "не заданы"}'
            )

    def _validate_size(self, size: Optional[int]) -> None:
        if size is None:
            return
        limit = self.submission_type.max_file_size_bytes()
        if size > limit:
            raise FileTooLarge(
                f'Файл {size / 1024 / 1024:.1f} МБ превышает лимит '
                f'{self.submission_type.max_file_size_mb} МБ'
            )

    def _validate_deadline(self) -> None:
        deadline = self.submission_type.deadline
        if deadline and timezone.now() > deadline and not self.submission_type.accept_late:
            raise DeadlinePassed(
                f'Срок сдачи истёк: {deadline.strftime("%d.%m.%Y %H:%M")}'
            )
