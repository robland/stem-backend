from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import attempts as service
from .attempt_serializers import (
    AnswerCreateSerializer,
    AnswerResultSerializer,
    AttemptSerializer,
    HintRequestSerializer,
    HintSerializer,
    SyncRequestSerializer,
    SyncResultSerializer,
)
from .models import Attempt


def _refused(error):
    return ValidationError({"detail": str(error)})


class AttemptViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AttemptSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Attempt.objects.none()
        return Attempt.objects.filter(user=self.request.user).select_related("exercise")

    @extend_schema(
        request=AnswerCreateSerializer,
        responses={
            201: AnswerResultSerializer,
            200: OpenApiResponse(AnswerResultSerializer, description="Réponse déjà reçue (même client_uuid)."),
            400: OpenApiResponse(description="Réponse mal formée, étape non en cours, tentative terminée."),
        },
        summary="Envoyer la réponse à l'étape en cours",
    )
    @action(detail=True, methods=["post"])
    def answers(self, request, pk=None):
        attempt = self.get_object()
        serializer = AnswerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            outcome = service.submit_answer(attempt, **serializer.validated_data)
        except service.AttemptError as e:
            raise _refused(e)
        attempt.refresh_from_db()
        data = AnswerResultSerializer({
            "is_correct": outcome.result.is_correct,
            "feedback": outcome.result.feedback,
            "details": outcome.result.details,
            "step": outcome.state,
            "explanation": outcome.explanation,
            "attempt": attempt,
        }).data
        return Response(data, status=status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK)

    @extend_schema(
        request=HintRequestSerializer,
        responses={200: HintSerializer, 400: OpenApiResponse(description="Étape non en cours ou indices épuisés.")},
        summary="Obtenir l'indice suivant de l'étape en cours",
        description="Chaque indice consulté réduit le score de l'étape (README §5.2).",
    )
    @action(detail=True, methods=["post"])
    def hints(self, request, pk=None):
        attempt = self.get_object()
        serializer = HintRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        step_id = serializer.validated_data["step_id"]
        try:
            hint, level, total = service.next_hint(attempt, step_id)
        except service.AttemptError as e:
            raise _refused(e)
        return Response(HintSerializer({"step_id": step_id, "hint": hint, "level": level, "total": total}).data)


class SyncView(APIView):
    @extend_schema(
        request=SyncRequestSerializer,
        responses={200: SyncResultSerializer},
        summary="Synchroniser les tentatives faites hors-ligne",
        description=(
            "Idempotent : les tentatives (id) et réponses (client_uuid) déjà reçues ne sont pas dupliquées. "
            "Le serveur recorrige chaque réponse ; son verdict fait foi."
        ),
    )
    def post(self, request):
        serializer = SyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = service.sync_attempts(request.user, serializer.validated_data["attempts"])
        return Response(SyncResultSerializer({"attempts": results}).data)
