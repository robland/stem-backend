#!/usr/bin/env bash
set -o errexit

pip install --no-cache-dir poetry
poetry lock
poetry install --no-interaction --no-ansi --only main --no-root

poetry run python  stem_learning_app/manage.py collectstatic --no-input

poetry run python  stem_learning_app/manage.py migrate

cd stem_learning_app/