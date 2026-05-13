from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bot_app", "0009_alter_tguser_options"),
        ("bot_send_file", "0002_data"),
    ]

    operations = [
        migrations.DeleteModel(
            name="BotCommand",
        ),
    ]
