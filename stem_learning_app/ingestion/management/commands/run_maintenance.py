from django.core.management.base import BaseCommand

from ingestion.services import purge_expired_files, recover_stuck_uploads
from learning.services import recover_stuck_generations


class Command(BaseCommand):
    help = (
        "Tâches périodiques sans celery beat (cron de l'hébergeur) : traitements bloqués "
        "et purge des fichiers expirés. À lancer toutes les 5 à 15 minutes."
    )

    def handle(self, *args, **options):
        relaunched, failed = recover_stuck_uploads()
        self.stdout.write(f"Uploads : {relaunched} relancé(s), {failed} mis en erreur.")
        relaunched, failed = recover_stuck_generations()
        self.stdout.write(f"Parcours : {relaunched} relancé(s), {failed} mis en erreur.")
        self.stdout.write(f"Fichiers expirés supprimés : {purge_expired_files()}.")
