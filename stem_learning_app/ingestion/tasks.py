from celery import shared_task

from . import services


@shared_task
def extract_upload(upload_id):
    services.run_extraction(upload_id)


@shared_task
def purge_expired_upload_files():
    return services.purge_expired_files()
