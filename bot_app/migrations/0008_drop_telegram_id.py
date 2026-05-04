"""Удаляем поле telegram_id у AuthToken и TgUser.

Поле было legacy: вся идентификация теперь идёт через
(platform, messenger_id), и для Telegram messenger_id == старый telegram_id.
Бэкфил данных был выполнен в миграции 0007, теперь поле можно убрать.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bot_app', '0007_platform_messenger_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='authtoken',
            name='telegram_id',
        ),
        migrations.RemoveField(
            model_name='tguser',
            name='telegram_id',
        ),
    ]
