"""Подключение расширения pgvector и модель SubmissionEmbedding.

Хранит BERT-эмбеддинги чанков работы — при повторных проверках
антиплагиата позволяет сравнивать без повторного BERT-инференса.
"""
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations, models
import django.db.models.deletion
import pgvector.django


class Migration(migrations.Migration):

    dependencies = [
        ('plagiarism', '0002_alter_plagiarismreport_options_and_more'),
        ('bot_send_file', '0010_rename_deadline_label'),
    ]

    operations = [
        CreateExtension('vector'),
        migrations.CreateModel(
            name='SubmissionEmbedding',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('chunk_index', models.PositiveSmallIntegerField(
                    verbose_name='Индекс чанка',
                )),
                ('embedding', pgvector.django.VectorField(
                    dimensions=312, verbose_name='Вектор',
                )),
                ('submission', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='embeddings',
                    to='bot_send_file.submission',
                    verbose_name='Работа',
                )),
            ],
            options={
                'verbose_name': 'Эмбеддинг работы',
                'verbose_name_plural': 'Эмбеддинги работ',
                'ordering': ['submission', 'chunk_index'],
                'unique_together': {('submission', 'chunk_index')},
            },
        ),
    ]
