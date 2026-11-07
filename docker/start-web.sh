#!/bin/sh
# Démarrage du service web en production : migrations puis gunicorn.
# Workers à threads (gthread) : un flux SSE ouvert (suivi d'extraction ou de génération)
# occupe un thread, pas un worker entier. Capacité = WEB_CONCURRENCY × GUNICORN_THREADS.
set -e

python manage.py migrate --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --worker-class gthread \
    --threads "${GUNICORN_THREADS:-16}" \
    --access-logfile -
