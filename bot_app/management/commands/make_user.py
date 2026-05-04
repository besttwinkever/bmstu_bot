"""Создать/обновить пользователя из CLI без захода в админку.

Примеры:

    # Преподаватель (попадает в группу "Сотрудник", может логиниться в /teacher/)
    python manage.py make_user ivanov --password Secret123 --first-name Иван --last-name Иванов --role teacher

    # Админ Django (is_superuser=True, is_staff=True — попадает в /bot-admin/)
    python manage.py make_user admin --password Secret123 --role admin

    # Студент (для отладки бота)
    python manage.py make_user student1 --password Secret123 --role student --academic-group ИУ5-21Б

Если пользователь уже существует — обновляются переданные поля и пароль.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


ROLE_GROUPS = {
    'student': 'Студент',
    'teacher': 'Сотрудник',
    'external': 'Сторонний',
}


class Command(BaseCommand):
    help = 'Создать или обновить пользователя с захэшированным паролем.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--password', required=True, help='Plain-text пароль; будет захэширован.')
        parser.add_argument('--first-name', default='')
        parser.add_argument('--last-name', default='')
        parser.add_argument('--email', default='')
        parser.add_argument(
            '--role',
            choices=['admin', 'teacher', 'student', 'external', 'none'],
            default='none',
            help='admin → суперюзер; teacher/student/external → добавляется в роль-группу.',
        )
        parser.add_argument(
            '--academic-group',
            default=None,
            help='Учебная группа (например, ИУ5-21Б). Создаётся, если её нет.',
        )

    def handle(self, *args, **opts):
        User = get_user_model()
        username = opts['username']

        user = User.objects.filter(username=username).first()
        created = user is None
        if created:
            user = User.objects.create_user(username=username, password=opts['password'])
            self.stdout.write(self.style.SUCCESS(f'Создан пользователь "{username}".'))
        else:
            user.set_password(opts['password'])
            self.stdout.write(self.style.WARNING(f'Пользователь "{username}" уже существует — пароль обновлён.'))

        if opts['first_name']:
            user.first_name = opts['first_name']
        if opts['last_name']:
            user.last_name = opts['last_name']
        if opts['email']:
            user.email = opts['email']

        role = opts['role']
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'teacher':
            # Преподавателю обычно нужен доступ к /teacher/, но не к Django-admin.
            # is_staff не выставляем — login_required в teacher-views этого не требует.
            pass

        user.save()

        if role in ROLE_GROUPS:
            group, _ = Group.objects.get_or_create(name=ROLE_GROUPS[role])
            user.groups.add(group)
            self.stdout.write(f'Добавлен в роль-группу "{group.name}".')

        if opts['academic_group']:
            ac_group, ac_created = Group.objects.get_or_create(name=opts['academic_group'])
            user.groups.add(ac_group)
            note = 'создана и добавлена' if ac_created else 'добавлена'
            self.stdout.write(f'Учебная группа "{ac_group.name}" — {note}.')

        self.stdout.write(self.style.SUCCESS('Готово.'))
