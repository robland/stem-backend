import json
from pathlib import Path

from django.conf import settings

from .schemas import ExerciseContent

# Consommé par le front (packages/content-schema) pour générer ses types Zod/TypeScript.
CONTENT_SCHEMA_PATH = Path(settings.BASE_DIR) / "schemas" / "exercise-content.schema.json"


def content_json_schema():
    return json.dumps(ExerciseContent.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
