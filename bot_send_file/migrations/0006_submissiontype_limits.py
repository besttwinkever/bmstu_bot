from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_send_file', '0005_submissiontype_deadline'),
    ]

    operations = [
        migrations.AddField(
            model_name='submissiontype',
            name='allowed_extensions',
            field=models.CharField(
                default='pdf,docx,doc,txt',
                help_text='Список расширений через запятую, например: pdf,docx,txt',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='submissiontype',
            name='max_file_size_mb',
            field=models.PositiveIntegerField(default=20),
        ),
    ]
