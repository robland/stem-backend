from .base import *  # noqa: F401,F403
from .base import env_bool, env_list, os

DEBUG = env_bool("DEBUG", True)

SECRET_KEY = os.environ.get("SECRET_KEY") or "django-insecure-dev-only-do-not-use-in-production"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

# En local, l'API est servie en HTTP.
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", False)

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
