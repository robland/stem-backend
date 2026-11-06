from celery import shared_task

from . import services


@shared_task
def generate_exercise_task(exercise_id):
    services.run_generation(exercise_id)
