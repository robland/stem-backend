from uuid import UUID

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from learning.attempt_serializers import AttemptSerializer
from learning.models import Exercise

from . import services
from .models import Challenge
from .serializers import (
    ChallengeCreateSerializer,
    ChallengeDetailSerializer,
    ChallengeReportSerializer,
    ChallengeSerializer,
    ChallengeStartSerializer,
    LeaderboardSerializer,
)

SCOPES = ["public", "mine", "joined"]


def _refused(error):
    return ValidationError({"detail": str(error)})


class ChallengePagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"


@extend_schema_view(
    list=extend_schema(
        summary="Catalogue des défis publics, mes défis ou les défis rejoints",
        parameters=[
            OpenApiParameter(
                "scope", str, enum=SCOPES,
                description="public (défaut) : catalogue des défis publics actifs ; mine : mes défis (tous statuts) ; "
                "joined : les défis que j'ai commencés.",
            ),
            OpenApiParameter("subject", str, description="Code de matière (catalogue)."),
            OpenApiParameter("level", str, description="Niveau (catalogue)."),
            OpenApiParameter("chapter", UUID, description="Chapitre (catalogue)."),
        ],
    ),
    retrieve=extend_schema(summary="Détail d'un défi et son parcours sans les réponses"),
)
class ChallengeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    pagination_class = ChallengePagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return Challenge.objects.none()
        user = self.request.user
        queryset = services.visible_to(user)
        if self.action == "list":
            queryset = self._scoped(user)
        return services.with_counts(queryset).select_related("exercise__subject", "author")

    def _scoped(self, user):
        params = self.request.query_params
        scope = params.get("scope", "public")
        if scope not in SCOPES:
            raise ValidationError({"scope": f"Valeurs possibles : {', '.join(SCOPES)}."})
        if scope == "mine":
            return Challenge.objects.filter(author=user)
        if scope == "joined":
            return Challenge.objects.filter(id__in=services.joined_ids(user))
        queryset = Challenge.objects.filter(visibility=Challenge.Visibility.PUBLIC, status=Challenge.Status.ACTIVE)
        if params.get("subject"):
            queryset = queryset.filter(exercise__subject__code=params["subject"])
        if params.get("level"):
            queryset = queryset.filter(exercise__level=params["level"])
        if params.get("chapter"):
            try:
                queryset = queryset.filter(exercise__chapter_id=UUID(params["chapter"]))
            except ValueError:
                raise ValidationError({"chapter": "Identifiant de chapitre invalide."})
        return queryset

    def get_serializer_class(self):
        return ChallengeSerializer if self.action == "list" else ChallengeDetailSerializer

    def _detail(self, challenge, status_code=status.HTTP_200_OK):
        challenge = services.with_counts(Challenge.objects.filter(id=challenge.id)).select_related(
            "exercise__subject", "author"
        ).get()
        return Response(ChallengeDetailSerializer(challenge, context={"request": self.request}).data, status=status_code)

    @extend_schema(
        request=ChallengeCreateSerializer,
        responses={
            201: ChallengeDetailSerializer,
            400: OpenApiResponse(description="Parcours pas prêt, pas encore terminé, ou déjà au catalogue."),
        },
        summary="Proposer un de mes parcours en défi",
        description="Privé : actif tout de suite (code de partage). Public : `pending` jusqu'à la vérification "
        "automatique de l'énoncé, puis `active` ou `rejected` (suivre via GET).",
    )
    def create(self, request):
        serializer = ChallengeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exercise = Exercise.objects.filter(id=data.pop("exercise"), owner=request.user).first()
        if exercise is None:
            raise ValidationError({"exercise": "Parcours introuvable."})
        try:
            challenge = services.create_challenge(request.user, exercise, **data)
        except services.ChallengeError as e:
            raise _refused(e)
        return self._detail(challenge, status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: ChallengeDetailSerializer, 404: OpenApiResponse(description="Aucun défi actif avec ce code.")},
        summary="Retrouver un défi par son code de partage",
    )
    @action(detail=False, methods=["get"], url_path=r"code/(?P<code>[A-Za-z0-9]{1,20})")
    def by_code(self, request, code=None):
        challenge = get_object_or_404(Challenge, code=code.upper(), status=Challenge.Status.ACTIVE)
        return self._detail(challenge)

    @extend_schema(
        request=ChallengeStartSerializer,
        responses={
            201: AttemptSerializer,
            200: OpenApiResponse(AttemptSerializer, description="Défi déjà commencé : ma tentative existante."),
            400: OpenApiResponse(description="Défi indisponible, code invalide, ou défi dont je suis l'auteur."),
        },
        summary="Relever un défi",
        description="Une seule tentative par élève, corrigée en ligne (pas de synchro hors-ligne). Réponses et "
        "indices : endpoints `attempts` habituels.",
    )
    @action(detail=True, methods=["post"])
    def attempts(self, request, pk=None):
        # Pas de get_object : un défi privé se rejoint avec son code, sans être encore « visible ».
        challenge = get_object_or_404(Challenge, pk=pk)
        serializer = ChallengeStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attempt, created = services.start_challenge_attempt(
                request.user, challenge,
                attempt_id=serializer.validated_data.get("id"), code=serializer.validated_data.get("code", ""),
            )
        except services.ChallengeError as e:
            raise _refused(e)
        return Response(AttemptSerializer(attempt).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(
        request=ChallengeReportSerializer,
        responses={
            201: OpenApiResponse(description="Signalement enregistré."),
            200: OpenApiResponse(description="Déjà signalé par cet élève."),
            400: OpenApiResponse(description="Défi dont je suis l'auteur."),
        },
        summary="Signaler un défi",
        description="Le défi est masqué à partir de 3 signalements, en attendant une relecture.",
    )
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        challenge = self.get_object()
        serializer = ChallengeReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            created = services.report_challenge(request.user, challenge, serializer.validated_data["reason"])
        except services.ChallengeError as e:
            raise _refused(e)
        return Response(status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(responses=LeaderboardSerializer, summary="Classement du défi")
    @action(detail=True, methods=["get"])
    def leaderboard(self, request, pk=None):
        return Response(LeaderboardSerializer(services.leaderboard(self.get_object(), request.user)).data)
