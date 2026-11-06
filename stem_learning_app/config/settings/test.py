import dj_database_url

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, os

DEBUG = False
SECRET_KEY = "test-secret-key-not-used-anywhere-else-0123456789"
ALLOWED_HOSTS = ["testserver"]
OPENAI_API_KEY = "test-openai-key"
# Jamais d'appel réel au LLM dans les tests (fixture fake_llm).
LLM_CLIENT = "llm.clients.fake.FakeLLMClient"

# DATABASE_URL est volontairement ignoré : les tests ne doivent jamais toucher
# une base réelle. TEST_DATABASE_URL (Postgres dans Docker) ou SQLite en mémoire.
DATABASES = {
    'default': dj_database_url.parse(os.environ.get("TEST_DATABASE_URL", "sqlite://:memory:"))
}

MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith("whitenoise")]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"

REFRESH_COOKIE_SECURE = False

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
