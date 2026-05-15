"""Переименование роль-группы «Сотрудник» → «Преподаватель».

Код бота и констант уже использует «Преподаватель», но в базе запись Group
могла остаться со старым именем. Миграция аккуратно меняет name, чтобы
существующие FK/M2M ссылки не потерялись.
"""
from django.db import migrations


def rename_forward(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Сотрудник').update(name='Преподаватель')


def rename_backward(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Преподаватель').update(name='Сотрудник')


class Migration(migrations.Migration):

    dependencies = [
        ('bot_app', '0010_delete_botcommand'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
