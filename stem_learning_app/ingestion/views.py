import hashlib

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from config import sse
from learning import services as learning_services
from learning.serializers import ExerciseSerializer

from . import services
from .documents import DocumentError, detect_file_type
from .models import ExtractedExercise, Upload
from .serializers import ExtractedExerciseSerializer, UploadCreateSerializer, UploadSerializer
from .tasks import extract_upload


class UploadViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = UploadSerializer
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Upload.objects.none()
        return Upload.objects.filter(user=self.request.user).prefetch_related("exercises__subject")

    @extend_schema(
        request={"multipart/form-data": UploadCreateSerializer},
        responses={
            201: UploadSerializer,
            200: OpenApiResponse(UploadSerializer, description="Document déjà envoyé : upload existant."),
            400: OpenApiResponse(description="Fichier refusé (type, taille, pages)."),
            429: OpenApiResponse(description="Quota journalier atteint (en-tête Retry-After)."),
        },
        summary="Envoyer un document d'exercices",
        description="L'extraction est asynchrone : suivre `status` via `GET /api/uploads/{id}/`.",
    )
    def create(self, request):
        serializer = UploadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data["file"].read()
        file_hash = hashlib.sha256(data).hexdigest()

        # Renvoi du même document (réseau instable, double clic) : idempotent et hors quota.
        existing = Upload.objects.filter(user=request.user, file_hash=file_hash).first()
        if existing and existing.status != Upload.Status.ERROR:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        try:
            file_type = detect_file_type(data)
        except DocumentError as e:
            raise ValidationError({"file": [str(e)]})

        if services.uploads_left_today(request.user) == 0:
            raise Throttled(
                wait=services.seconds_until_quota_reset(),
                detail="Tu as atteint le nombre de documents autorisés aujourd'hui.",
            )

        try:
            with transaction.atomic():
                if existing:
                    # Un document en erreur peut être renvoyé : on repart d'un upload neuf.
                    existing.delete()
                upload = Upload(user=request.user, file_type=file_type, file_size=len(data), file_hash=file_hash)
                upload.file.save("document", ContentFile(data), save=False)
                upload.save()
                transaction.on_commit(lambda: extract_upload.delay(str(upload.id)))
        except IntegrityError:
            upload.file.delete(save=False)
            existing = Upload.objects.get(user=request.user, file_hash=file_hash)
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        return Response(self.get_serializer(upload).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses=sse.event_stream_response(
            "Flux SSE : un événement par statut (`pending`, `reading`, puis `extracted` ou `error`, qui "
            "terminent le flux), `data` = l'upload comme dans `GET /api/uploads/{id}/`."
        ),
        summary="Suivre l'extraction en direct (SSE)",
    )
    @action(detail=True, methods=["get"], renderer_classes=[JSONRenderer, sse.EventStreamRenderer])
    def events(self, request, pk=None):
        upload = self.get_object()
        queryset = self.get_queryset()

        def snapshot():
            current = queryset.filter(pk=upload.pk).first()
            return current and (current.status, UploadSerializer(current).data)

        return sse.stream(snapshot, terminal={Upload.Status.EXTRACTED, Upload.Status.ERROR})


@extend_schema_view(
    partial_update=extend_schema(summary="Corriger un énoncé extrait (matière, niveau, chapitre)"),
    destroy=extend_schema(summary="Écarter un énoncé extrait non validé"),
)
class ExtractedExerciseViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = ExtractedExerciseSerializer
    http_method_names = ["patch", "delete", "post"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return ExtractedExercise.objects.none()
        return ExtractedExercise.objects.filter(
            upload__user=self.request.user, upload__status=Upload.Status.EXTRACTED
        ).select_related("upload", "subject", "chapter")

    def perform_destroy(self, instance):
        if instance.validated_at:
            raise ValidationError("Énoncé déjà validé : il ne peut plus être supprimé.")
        upload = instance.upload
        instance.delete()
        services.delete_file_if_done(upload)

    @extend_schema(
        request=None,
        responses={200: ExtractedExerciseSerializer, 400: OpenApiResponse(description="Matière ou niveau manquant.")},
        summary="Valider un énoncé extrait",
        description="Le document d'origine est supprimé dès que tous ses énoncés sont validés.",
    )
    @action(detail=True, methods=["post"], url_path="validate")
    def confirm(self, request, pk=None):
        exercise = self.get_object()
        if not exercise.validated_at:
            missing = {
                field: "Champ requis pour valider l'énoncé."
                for field, value in (("subject", exercise.subject), ("level", exercise.level))
                if not value
            }
            if missing:
                raise ValidationError(missing)
            services.validate_exercise(exercise)
        return Response(self.get_serializer(exercise).data)

    @extend_schema(
        request=None,
        responses={
            202: OpenApiResponse(ExerciseSerializer, description="Génération lancée : suivre generation_status."),
            200: OpenApiResponse(ExerciseSerializer, description="Parcours existant ou repris du cache."),
            400: OpenApiResponse(description="Énoncé non validé ou matière non ouverte."),
            429: OpenApiResponse(description="Quota journalier atteint (en-tête Retry-After)."),
        },
        summary="Générer le parcours guidé d'un énoncé validé",
        description="Suivre l'avancement via `GET /api/exercises/{id}/`.",
    )
    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        extracted = self.get_object()
        try:
            exercise, launched = learning_services.request_generation(extracted)
        except learning_services.GenerationRefused as e:
            raise ValidationError(str(e))
        except learning_services.QuotaExceeded as e:
            raise Throttled(wait=e.wait, detail="Tu as atteint le nombre de parcours autorisés aujourd'hui.")
        return Response(
            ExerciseSerializer(exercise).data,
            status=status.HTTP_202_ACCEPTED if launched else status.HTTP_200_OK,
        )
