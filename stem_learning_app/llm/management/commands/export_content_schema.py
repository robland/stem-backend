from django.core.management.base import BaseCommand

from llm.content_schema import CONTENT_SCHEMA_PATH, content_json_schema


class Command(BaseCommand):
    help = "Écrit le JSON Schema du contenu des parcours (README §6) pour le front."

    def handle(self, *args, **options):
        CONTENT_SCHEMA_PATH.write_text(content_json_schema(), encoding="utf-8")
        self.stdout.write(f"Schéma écrit : {CONTENT_SCHEMA_PATH}")
