import os
from celery import Celery, shared_task
from dotenv import load_dotenv
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# os.environ.setdefault("OPENAI_API_KEY", "")
load_dotenv()
# print("===============================", settings.OPENAI_API_KEY)
app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


@shared_task
def debug_openai_key():
    from django.conf import settings
    print("OPENAI KEY =", settings.OPENAI_API_KEY)
