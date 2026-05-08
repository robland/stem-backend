# Dockerfile
FROM python:3.11-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#dossier de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev  \
      curl  \
      ca-certificates \
      && rm -rf /var/lib/apt/lists/*

# Installation de Poetry
RUN pip install  poetry gunicorn

# On copie uniquement les dépendances
COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false  && poetry install --no-root --no-interaction --no-ansi
RUN poetry add gunicorn

# On copie le code

COPY . /app/

# Collect static
# RUN python manage.py collectstatic --noinput

# Commande d'entrée
CMD ["gunicorn", "stem_learning_app.config.wsgi:application", "--bind", "0.0.0.0:8000"]


