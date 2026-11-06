from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Exercise, Subject, Chapter, Step, QCM
from .serializer import (
    UploadDocumentSerializer, SubjectSerializer, ChapterSerializer,
    ExerciseSerializer, StepSerializer, QCMSerializer,
)
from .tasks import process_document_pipeline
from .utils import calculate_file_hash


class DocumentUploadView(APIView):
    serializer_class = UploadDocumentSerializer
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_hash = calculate_file_hash(uploaded_file)

        document, created = Document.objects.get_or_create(
            file_hash=file_hash,
            defaults={
                "user": request.user,
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
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


@extend_schema(request=None, responses={202: None})
@api_view(["POST"])
@permission_classes([IsAdminUser])
def process_document(request, pk):
    """Relance l'analyse d'un document (administration)."""
    document = get_object_or_404(Document, pk=pk)
    process_document_pipeline.delay(str(document.id))
    return Response(status=status.HTTP_202_ACCEPTED)


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Chapter.objects.select_related("subject").all()
    serializer_class = ChapterSerializer

    def get_queryset(self):
        queryset = Chapter.objects.select_related("subject").all()
        subject_id = self.request.query_params.get("subject_id")

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        return queryset


class ExerciseView(APIView):
    serializer_class = ExerciseSerializer

    def get(self, request):
        queryset = Exercise.objects.all()
        document_id = request.GET.get("id")

        if document_id:
            queryset = queryset.filter(document__id=document_id)

        return Response(
            ExerciseSerializer(
                queryset,
                many=True,
                context={"request": request}
            ).data,
            status=status.HTTP_200_OK
        )


class ExerciseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Exercise.objects.all().prefetch_related("progress")
    serializer_class = ExerciseSerializer


class StepView(APIView):
    serializer_class = StepSerializer

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
    serializer_class = QCMSerializer

    def get(self, request, id):
        queryset = QCM.objects.filter(step__id=id)
        return Response(
            QCMSerializer(
                queryset,
                many=True
            ).data,
            status=status.HTTP_200_OK
        )
