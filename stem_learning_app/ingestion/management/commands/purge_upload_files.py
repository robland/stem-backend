from django.core.management.base import BaseCommand

from ingestion.services import purge_expired_files


class Command(BaseCommand):
    help = "Supprime les fichiers d'upload conservés au-delà de UPLOAD_FILE_RETENTION_HOURS (à planifier)."

    def handle(self, *args, **options):
        count = purge_expired_files()
        self.stdout.write(f"{count} fichier(s) supprimé(s).")
