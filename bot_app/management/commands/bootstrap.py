"""Создаёт администраторов с дефолтным паролем по списку username'ов.

    python manage.py bootstrap имя1,имя2,...

Используется один раз при первом развёртывании. Существующие пользователи
не перезаписываются — только сообщается, что они уже есть.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from oauth.models import OauthUser


DEFAULT_PASSWORD = 'ChangeMe123!'


class Command(BaseCommand):
    help = 'Создаёт администраторов Django с дефолтным паролем (ChangeMe123!).'

    def add_arguments(self, parser):
        parser.add_argument(
            'admins',
            type=str,
            help='Список username администраторов через запятую.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        usernames = [name.strip() for name in options['admins'].split(',') if name.strip()]
        for username in usernames:
            if OauthUser.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(
                    f'Пользователь «{username}» уже существует — пропускаю.'
                ))
                continue
            OauthUser.objects.create_user(
                username,
                password=DEFAULT_PASSWORD,
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS(
                f'Создан администратор «{username}» (пароль: {DEFAULT_PASSWORD}).'
            ))
