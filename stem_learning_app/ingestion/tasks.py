from celery import shared_task

from . import services


@shared_task
def extract_upload(upload_id):
    services.run_extraction(upload_id)


@shared_task
def purge_expired_upload_files():
    return services.purge_expired_files()


@shared_task
def run_maintenance():
    """Relance ou met en erreur les traitements bloqués (uploads, générations, modérations de défis)."""
    from challenges.services import recover_pending_moderations
    from learning.services import recover_stuck_generations

    return {
        "uploads": services.recover_stuck_uploads(),
        "generations": recover_stuck_generations(),
        "moderations": recover_pending_moderations(),
    }
