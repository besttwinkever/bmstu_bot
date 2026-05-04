from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bot_send_file', '0006_submissiontype_limits'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlagiarismReport',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                )),
                ('shingle_score', models.FloatField(blank=True, null=True)),
                ('bert_score', models.FloatField(blank=True, null=True)),
                ('verdict', models.CharField(
                    choices=[
                        ('pending', 'В очереди'),
                        ('unsupported', 'Формат не поддерживается'),
                        ('error', 'Ошибка проверки'),
                        ('original', 'Оригинал'),
                        ('suspicious', 'Подозрение на рерайт'),
                        ('plagiarism', 'Плагиат'),
                    ],
                    default='pending',
                    max_length=32,
                )),
                ('details', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('matched_with', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='plagiarism_matches',
                    to='bot_send_file.submission',
                )),
                ('submission', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='plagiarism_report',
                    to='bot_send_file.submission',
                )),
            ],
        ),
    ]
