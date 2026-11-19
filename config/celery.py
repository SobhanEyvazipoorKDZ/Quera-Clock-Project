import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from celery import Celery

app = Celery("quera_clock")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
