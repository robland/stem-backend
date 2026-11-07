from uuid import UUID

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from curriculum.choices import Level
from learning.serializers import NULLABLE_OBJECT
from llm.services import exam_for

from . import services
from .models import Challenge, ChallengeReport

# Motifs de refus de la modération automatique, expliqués à l'auteur.
MODERATION_MESSAGES = {
    "personal_data": "L'énoncé contient des informations personnelles (nom, établissement, téléphone…).",
    "inappropriate": "L'énoncé contient un contenu inapproprié.",
    "not_schoolwork": "Le texte ne ressemble pas à un exercice scolaire.",
}


class ChallengeSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="exercise.title", read_only=True)
    subject = serializers.SlugRelatedField(source="exercise.subject", slug_field="code", read_only=True)
    level = serializers.ChoiceField(source="exercise.level", choices=Level.choices, read_only=True)
    chapter = serializers.PrimaryKeyRelatedField(source="exercise.chapter", read_only=True)
    exam = serializers.SerializerMethodField(help_text="Examen visé : BEPC (collège) ou BAC (lycée).")
    author = serializers.CharField(source="author.pseudo", read_only=True, help_text="Pseudo de l'auteur.")
    is_author = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField(help_text="Élèves ayant commencé le défi.")
    finished = serializers.SerializerMethodField(help_text="Élèves ayant terminé le défi.")
    code = serializers.SerializerMethodField(help_text="Code de partage ; visible par l'auteur seulement.")
    moderation_messages = serializers.SerializerMethodField(
        help_text="Raisons d'un refus de publication ; pour l'auteur seulement."
    )
    author_points = serializers.SerializerMethodField(
        help_text="Points gagnés par l'auteur avec ce défi (10 par participant qui termine, 50 au plus)."
    )

    class Meta:
        model = Challenge
        fields = [
            "id", "title", "subject", "level", "chapter", "exam", "visibility", "timed", "hints_allowed",
            "status", "author", "is_author", "participants", "finished", "code", "moderation_messages",
            "author_points", "created_at",
        ]
        read_only_fields = fields

    def _is_author(self, obj):
        request = self.context.get("request")
        return bool(request) and obj.author_id == request.user.id

    def get_exam(self, obj) -> str:
        return exam_for(obj.exercise.level)

    def get_is_author(self, obj) -> bool:
        return self._is_author(obj)

    def get_participants(self, obj) -> int:
        return obj.participants_count if hasattr(obj, "participants_count") else obj.attempts.count()

    def get_finished(self, obj) -> int:
        if hasattr(obj, "finished_count"):
            return obj.finished_count
        return obj.attempts.filter(finished_at__isnull=False).count()

    def get_code(self, obj) -> str | None:
        return obj.code if self._is_author(obj) else None

    def get_moderation_messages(self, obj) -> list[str]:
        if not self._is_author(obj):
            return []
        return [MODERATION_MESSAGES[reason] for reason in obj.moderation_reasons if reason in MODERATION_MESSAGES]

    def get_author_points(self, obj) -> int | None:
        return services.points_for(self.get_finished(obj)) if self._is_author(obj) else None


class ChallengeDetailSerializer(ChallengeSerializer):
    content = serializers.SerializerMethodField(
        help_text=(
            "Parcours sans les réponses (comme GET /api/exercises/{id}/), sans aucun indice si `hints_allowed` "
            "est faux ; null tant que le défi n'est pas actif."
        )
    )
    my_attempt = serializers.SerializerMethodField(help_text="Ma tentative sur ce défi (une seule) ; null sinon.")

    class Meta(ChallengeSerializer.Meta):
        fields = ChallengeSerializer.Meta.fields + ["content", "my_attempt"]
        read_only_fields = fields

    @extend_schema_field(NULLABLE_OBJECT)
    def get_content(self, obj):
        if obj.status != Challenge.Status.ACTIVE:
            return None
        return services.challenge_content(obj)

    def get_my_attempt(self, obj) -> UUID | None:
        request = self.context.get("request")
        attempt = request and obj.attempts.filter(user=request.user).first()
        return str(attempt.id) if attempt else None


class ChallengeCreateSerializer(serializers.Serializer):
    exercise = serializers.UUIDField(help_text="Parcours de l'élève, prêt et déjà terminé une fois.")
    visibility = serializers.ChoiceField(choices=Challenge.Visibility.choices)
    timed = serializers.BooleanField(default=False, help_text="Chrono affiché pendant la résolution.")
    hints_allowed = serializers.BooleanField(default=True)


class ChallengeStartSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, help_text="Généré par le client : rend l'appel idempotent.")
    code = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text="Requis pour un défi privé.")


class ChallengeReportSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=ChallengeReport.Reason.choices)


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    pseudo = serializers.CharField()
    score = serializers.IntegerField()
    duration_seconds = serializers.IntegerField(help_text="Du démarrage à la fin (heure du serveur).")
    is_me = serializers.BooleanField()


class LeaderboardSerializer(serializers.Serializer):
    participants = serializers.IntegerField()
    finished = serializers.IntegerField()
    entries = LeaderboardEntrySerializer(many=True, help_text="Score décroissant, puis durée, puis ordre d'arrivée.")
    me = LeaderboardEntrySerializer(allow_null=True, help_text="Ma place, même hors des premiers affichés.")
