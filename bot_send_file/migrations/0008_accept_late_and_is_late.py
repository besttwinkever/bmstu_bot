from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_send_file', '0007_alter_submission_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='submissiontype',
            name='accept_late',
            field=models.BooleanField(
                default=False,
                help_text='Принимать работы после дедлайна (с пометкой «с опозданием»).',
            ),
        ),
        migrations.AddField(
            model_name='submission',
            name='is_late',
            field=models.BooleanField(default=False),
        ),
    ]
