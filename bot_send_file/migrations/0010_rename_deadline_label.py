from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_send_file', '0009_alter_submission_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submissiontype',
            name='deadline',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Срок сдачи'),
        ),
        migrations.AlterField(
            model_name='submissiontype',
            name='accept_late',
            field=models.BooleanField(
                default=False,
                help_text='Если включено — поздние работы принимаются с пометкой «с опозданием».',
                verbose_name='Принимать после срока сдачи',
            ),
        ),
    ]
