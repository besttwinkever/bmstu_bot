"""Создать демо-данные для отладки бота и антиплагиата.

Что появится:
* учебная группа «Демо ИУ5-21Б» + роль-группы Студент/Сотрудник;
* преподаватель `demo_teacher` (пароль Secret123);
* три студента: `demo_alice`, `demo_bob`, `demo_carol` (пароль Secret123);
* дисциплина «Демо-курс» — преподаватель demo_teacher, группа «Демо ИУ5-21Б»;
* тип работы «Лабораторная 1» с дедлайном +30 дней и accept_late=True;
* три уже сданные работы (txt) — две похожих и одна оригинальная,
  чтобы антиплагиат сразу было что показывать.

Запуск:
    python manage.py seed_demo
    python manage.py seed_demo --reset   # снести и пересоздать всё демо
"""
from __future__ import annotations

import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from bot_app.models import Discipline
from bot_send_file.models import Submission, SubmissionType
from bot_send_file.services.submission import sanitize_path_component


DEFAULT_PASSWORD = 'Secret123'

ACADEMIC_GROUP = 'Демо ИУ5-21Б'
ROLE_STUDENT = 'Студент'
ROLE_STAFF = 'Сотрудник'

TEACHER = ('demo_teacher', 'Иван', 'Петров')
STUDENTS = [
    ('demo_alice', 'Алиса', 'Иванова'),
    ('demo_bob', 'Борис', 'Сидоров'),
    ('demo_carol', 'Кира', 'Орлова'),
]

DISCIPLINE_NAME = 'Демо-курс'
SUBMISSION_TYPE_NAME = 'Лабораторная 1'

# Тексты подобраны так, чтобы alice/bob были «похожи» (рерайт), а carol — иной.
TEXTS = {
    'demo_alice': (
        'alice.txt',
        'В данной работе рассматривается задача сортировки массива методом '
        'пузырька. Алгоритм проходит по массиву и сравнивает соседние '
        'элементы, обменивая их местами при необходимости. Сложность '
        'алгоритма составляет O(n^2) в худшем случае.'
    ),
    'demo_bob': (
        'bob.txt',
        'В работе рассматривается задача сортировки массива методом '
        'пузырька. Алгоритм проходит по массиву и сравнивает соседние '
        'элементы, обменивая их местами при необходимости. Сложность '
        'алгоритма O(n^2) в худшем случае.'
    ),
    'demo_carol': (
        'carol.txt',
        'Цель данной работы — изучение быстрой сортировки. Алгоритм '
        'выбирает опорный элемент, разбивает массив на две части и '
        'рекурсивно сортирует подмассивы. Средняя сложность O(n log n).'
    ),
}


class Command(BaseCommand):
    help = 'Создать демо-данные для отладки бота и антиплагиата.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Удалить демо-объекты перед созданием.')

    def handle(self, *args, **opts):
        if opts['reset']:
            self._reset()

        academic_group, _ = Group.objects.get_or_create(name=ACADEMIC_GROUP)
        student_role, _ = Group.objects.get_or_create(name=ROLE_STUDENT)
        staff_role, _ = Group.objects.get_or_create(name=ROLE_STAFF)

        teacher = self._upsert_user(*TEACHER, role=staff_role, academic=academic_group)
        students = [
            self._upsert_user(*s, role=student_role, academic=academic_group)
            for s in STUDENTS
        ]

        discipline, created = Discipline.objects.get_or_create(name=DISCIPLINE_NAME)
        discipline.teachers.add(teacher)
        discipline.groups.add(academic_group)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Создана дисциплина «{DISCIPLINE_NAME}».'))

        submission_type, st_created = SubmissionType.objects.update_or_create(
            name=SUBMISSION_TYPE_NAME,
            discipline=discipline,
            defaults={
                'deadline': timezone.now() + timedelta(days=30),
                'accept_late': True,
                'allowed_extensions': 'txt,pdf,docx',
                'max_file_size_mb': 10,
            },
        )
        if st_created:
            self.stdout.write(self.style.SUCCESS(f'Создан тип работы «{SUBMISSION_TYPE_NAME}».'))

        for student in students:
            self._upload_demo_submission(student, submission_type)

        self.stdout.write(self.style.SUCCESS(
            '\nГотово. Логин/пароль для всех демо-юзеров: <username> / Secret123\n'
            '— teacher: demo_teacher (вход на /teacher/)\n'
            '— students: demo_alice, demo_bob, demo_carol\n'
            'В боте используйте /su <username> чтобы переключаться между ними.'
        ))

    # --------------------------------------------------------------

    def _upsert_user(self, username, first_name, last_name, role: Group, academic: Group):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(DEFAULT_PASSWORD)
            self.stdout.write(self.style.SUCCESS(f'Создан пользователь {username}.'))
        else:
            self.stdout.write(f'Пользователь {username} уже существует — обновляю поля.')
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.save()
        user.groups.add(role, academic)
        return user

    def _upload_demo_submission(self, user, submission_type):
        if Submission.objects.filter(user=user, submission_type=submission_type).exists():
            self.stdout.write(f'  • {user.username}: работа уже сдана, пропускаю.')
            return

        file_name, text = TEXTS.get(user.username, (f'{user.username}.txt', 'Демо-работа.'))
        rel_dir = os.path.join(
            'submissions',
            sanitize_path_component(submission_type.discipline.name, 'discipline'),
            sanitize_path_component(submission_type.name, 'assignment'),
            sanitize_path_component(
                user.get_full_name() or user.username, 'user',
            ),
        )
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        abs_path = os.path.join(abs_dir, file_name)
        with open(abs_path, 'w', encoding='utf-8') as fp:
            fp.write(text)

        submission = Submission.objects.create(
            submission_type=submission_type,
            user=user,
        )
        submission.file.name = os.path.join(rel_dir, file_name).replace('\\', '/')
        submission.save(update_fields=['file'])
        self.stdout.write(self.style.SUCCESS(
            f'  • {user.username}: создана демо-работа {file_name} '
            '(post_save сигнал запустит антиплагиат).'
        ))

    def _reset(self):
        usernames = [TEACHER[0]] + [s[0] for s in STUDENTS]
        User = get_user_model()
        # Submission на этих пользователей удалится каскадом.
        deleted_users, _ = User.objects.filter(username__in=usernames).delete()
        deleted_disc, _ = Discipline.objects.filter(name=DISCIPLINE_NAME).delete()
        self.stdout.write(self.style.WARNING(
            f'Reset: удалено пользователей={deleted_users}, дисциплин={deleted_disc}'
        ))
