from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from . import attempts as attempt_service
from .attempt_serializers import AttemptSerializer, AttemptStartSerializer
from .models import Exercise
from .serializers import ExerciseDetailSerializer, ExerciseOfflineSerializer, ExerciseSerializer


class ExercisePagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"


@extend_schema_view(
    list=extend_schema(summary="Mes parcours"),
    retrieve=extend_schema(summary="Parcours sans les réponses attendues"),
)
class ExerciseViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = ExercisePagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Exercise.objects.none()
        # V1 : uniquement ses propres parcours (les défis viendront en V2).
        return Exercise.objects.filter(owner=self.request.user).select_related("subject")

    def get_serializer_class(self):
        if self.action == "list":
            return ExerciseSerializer
        if self.action == "offline":
            return ExerciseOfflineSerializer
        if self.action == "attempts":
            return AttemptStartSerializer
        return ExerciseDetailSerializer

    @extend_schema(
        summary="Parcours complet pour la correction hors-ligne",
        description="Inclut les réponses attendues : réservé au propriétaire du parcours, jamais aux défis.",
    )
    @action(detail=True, methods=["get"])
    def offline(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(
        request=AttemptStartSerializer,
        responses={
            201: AttemptSerializer,
            200: OpenApiResponse(AttemptSerializer, description="Tentative déjà créée (même id)."),
            400: OpenApiResponse(description="Parcours pas encore prêt."),
        },
        summary="Démarrer une tentative",
    )
    @action(detail=True, methods=["post"])
    def attempts(self, request, pk=None):
        exercise = self.get_object()
        serializer = AttemptStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attempt, created = attempt_service.start_attempt(
                request.user, exercise,
                serializer.validated_data.get("id"), serializer.validated_data.get("started_at"),
            )
        except attempt_service.AttemptError as e:
            raise ValidationError({"detail": str(e)})
        return Response(AttemptSerializer(attempt).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
