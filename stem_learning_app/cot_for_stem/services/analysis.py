import json

from celery import shared_task, chain
from ..models import Exercise, Document, Subject, Chapter
from ..services.openai_vision import ExerciseVisionService
from .qcm import generate_qcm
from django.utils.html import escape


@shared_task
def analyze_document(document_id):

    document = Document.objects.get(id=document_id)

    document.processing_status = "analyzing"
    document.save()

    raw_text = ExerciseVisionService.analyze_exercise(
        file_url=document.file.path
    )
    # json_text = raw_text[7:len(raw_text)-3].strip()
    json_text = raw_text.strip()
    with open("./openai.response.json", "w") as f:
        f.write(json_text)

    json_object = json.loads(json_text)

    for index, value in enumerate(json_object):

        subject, created = Subject.objects.get_or_create(name=value['subject'])
        chapter, created = Chapter.objects.get_or_create(
            name=value['chapter'],
            subject=subject
        )

        exercise = Exercise.objects.create(
            title=value['title'],
            document=document,
            chapter=chapter,
            level=value['level'],
            statement=value['statement'],
            formula=value['formula_recall'],
            concepts_used=value['concepts_used'],
            intuition=value['intuition'],
            raw_text=value
        )
        generate_qcm.delay(str(exercise.id))

    return str(document.id)
