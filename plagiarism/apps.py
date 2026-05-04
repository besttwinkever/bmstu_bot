from django.apps import AppConfig


class PlagiarismConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plagiarism'
    verbose_name = 'Антиплагиат'

    def ready(self):
        # Сигнал post_save запускает проверку при создании Submission.
        from . import signals  # noqa: F401
