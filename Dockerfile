# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# base : Python + uv + dépendances de production
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev

# ---------------------------------------------------------------------------
# dev : + dépendances de développement (pytest…). Le code est monté en volume.
# ---------------------------------------------------------------------------
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked

WORKDIR /app/stem_learning_app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# prod (cible par défaut) : code copié, statiques collectés, utilisateur non root
# ---------------------------------------------------------------------------
FROM base AS prod

COPY pyproject.toml uv.lock /app/
COPY stem_learning_app /app/stem_learning_app
COPY docker/start-web.sh /app/docker/start-web.sh

WORKDIR /app/stem_learning_app

ENV DJANGO_SETTINGS_MODULE=config.settings.prod

# collectstatic n'a besoin d'aucun secret réel.
RUN SECRET_KEY=collectstatic ALLOWED_HOSTS=localhost DATABASE_URL=sqlite:// \
    python manage.py collectstatic --noinput \
    && useradd --system --uid 1000 --no-create-home app \
    && mkdir -p /app/stem_learning_app/media \
    && chown -R app /app/stem_learning_app/media

USER app

EXPOSE 8000
CMD ["sh", "/app/docker/start-web.sh"]
