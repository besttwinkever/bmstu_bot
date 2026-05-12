import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bauman_event_tg_bot.settings')

app = Celery('bauman_event_tg_bot')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-scheduled-notifications-every-minute': {
        'task': 'bot_app.tasks.send_scheduled_notifications',
        'schedule': 60.0,
    },
}
