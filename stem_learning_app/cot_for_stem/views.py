# views.py
import json

from django.http import HttpResponse
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets

from .services.openai_vision import ExerciseVisionService

from .models import Document, Exercise
from .tasks import process_document_pipeline
from .utils import calculate_file_hash

from .serializer import *


class DocumentUploadView(APIView):
    serializer_class = UploadDocumentSerializer

    def post(self, request):
        uploaded_file = request.data["file"]

        if not uploaded_file:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_hash = calculate_file_hash(uploaded_file)

        document, created = Document.objects.get_or_create(
            file_hash=file_hash,
            defaults={
                "file": uploaded_file,
                "file_type": "pdf" if uploaded_file.name.endswith(".pdf") else "image",
                "original_filename": uploaded_file.name,
                "file_size": uploaded_file.size,
            }
        )

        if created:
            process_document_pipeline.delay(str(document.id))

        return Response(
            {
                "document_id": document.id,
                "status": "processing" if created else "already_processed"
            },
            status=status.HTTP_201_CREATED
        )


def process_document(request, pk):
    document = Document.objects.get(pk=pk)
    process_document_pipeline.delay(str(document.id))
    return HttpResponse("Document processed!")


def process_exercise(request, pk):
    exercise = Exercise.objects.get(pk=pk)
    raw_text = exercise.raw_text
    json_part = raw_text[7:len(raw_text)-3]
    json_object = json.loads(json_part)

    for k in json_object.keys():
        Exercise.objects.create(
        )
    return HttpResponse(f"Document: {json_object.keys()}")


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.select_related("subject").all()
    serializer_class = ChapterSerializer

    def get_queryset(self):
        queryset = Chapter.objects.select_related("subject").all()
        subject_id = self.request.query_params.get("subject_id")

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        return queryset


class ExerciseView(APIView):
    """
    Reçoit un fichier (déjà uploadé sur S3 ou autre)
    et déclenche l’analyse pédagogique.
    """
    def get(self, request):
        queryset = Exercise.objects.all()
        document_id = request.GET.get("id")

        if document_id:
            queryset.filter(document__id=document_id)

        return Response(
            ExerciseSerializer(
                queryset,
                many=True
            ).data,
            status=status.HTTP_200_OK
        )


class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all().prefetch_related("progress")
    serializer_class = ExerciseSerializer


class StepView(APIView):
    def get(self, request, id):
        queryset = Step.objects.filter(exercise__id=id)
        return Response(
            StepSerializer(
                queryset,
                many=True
            ).data,
            status=status.HTTP_200_OK
        )


class QCMView(APIView):
    def get(self, request, id):
        queryset = QCM.objects.filter(step__id=id)
        return Response(
            QCMSerializer(
                queryset,
                many=True
            ).data,
            status=status.HTTP_200_OK
        )
