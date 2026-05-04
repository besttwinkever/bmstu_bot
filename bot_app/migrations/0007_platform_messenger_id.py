from django.db import migrations, models


def backfill_messenger_ids(apps, schema_editor):
    AuthToken = apps.get_model('bot_app', 'AuthToken')
    TgUser = apps.get_model('bot_app', 'TgUser')

    for token in AuthToken.objects.all().only('id', 'platform', 'messenger_id', 'telegram_id'):
        updates = []
        if not token.platform:
            token.platform = 'telegram'
            updates.append('platform')
        if not token.messenger_id and token.telegram_id:
            token.messenger_id = token.telegram_id
            updates.append('messenger_id')
        if updates:
            token.save(update_fields=updates)

    for tg_user in TgUser.objects.all().only('id', 'platform', 'messenger_id', 'telegram_id'):
        updates = []
        if not tg_user.platform:
            tg_user.platform = 'telegram'
            updates.append('platform')
        if not tg_user.messenger_id and tg_user.telegram_id:
            tg_user.messenger_id = tg_user.telegram_id
            updates.append('messenger_id')
        if updates:
            tg_user.save(update_fields=updates)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('bot_app', '0006_alter_authtoken_options_alter_botcommand_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='authtoken',
            name='platform',
            field=models.CharField(default='telegram', max_length=32, verbose_name='Платформа'),
        ),
        migrations.AddField(
            model_name='authtoken',
            name='messenger_id',
            field=models.CharField(default='', max_length=255, verbose_name='ID мессенджера'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='authtoken',
            name='telegram_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID Telegram'),
        ),
        migrations.AddField(
            model_name='tguser',
            name='platform',
            field=models.CharField(default='telegram', max_length=32, verbose_name='Платформа'),
        ),
        migrations.AddField(
            model_name='tguser',
            name='messenger_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID мессенджера'),
        ),
        migrations.AddConstraint(
            model_name='tguser',
            constraint=models.UniqueConstraint(fields=('platform', 'messenger_id'), name='unique_messenger_user'),
        ),
        migrations.RunPython(backfill_messenger_ids, reverse_code=noop_reverse),
    ]
