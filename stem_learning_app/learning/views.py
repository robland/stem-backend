from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

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
        return ExerciseDetailSerializer

    @extend_schema(
        summary="Parcours complet pour la correction hors-ligne",
        description="Inclut les réponses attendues : réservé au propriétaire du parcours, jamais aux défis.",
    )
    @action(detail=True, methods=["get"])
    def offline(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)
