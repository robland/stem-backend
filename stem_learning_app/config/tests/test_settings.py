import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]


def dev_setting(expression, **env):
    """Évalue un réglage de `config.settings.dev` dans un processus neuf (les settings de test sont déjà chargés)."""
    environ = os.environ | {"DJANGO_SETTINGS_MODULE": "config.settings.dev"} | env
    code = f"import django; django.setup(); from django.conf import settings; print({expression})"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_DIR, env=environ, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def test_empty_variables_from_env_example_fall_back_to_defaults():
    # .env.example contient `DATABASE_URL=` vide : sans repli, Django prendrait le moteur « dummy ».
    engine = dev_setting("settings.DATABASES['default']['ENGINE']", DATABASE_URL="", CELERY_BROKER_URL="")
    broker = dev_setting("settings.CELERY_BROKER_URL", DATABASE_URL="", CELERY_BROKER_URL="")

    assert (engine, broker) == ("django.db.backends.sqlite3", "redis://localhost:6379/0")
