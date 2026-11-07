from celery import shared_task

from . import services


@shared_task
def moderate_challenge_task(challenge_id):
    services.run_moderation(challenge_id)
