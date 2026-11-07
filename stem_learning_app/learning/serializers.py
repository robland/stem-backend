from uuid import UUID

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from llm.services import exam_for

from .attempts import resumable_attempt
from .models import Exercise
from .services import public_content


class ExerciseSerializer(serializers.ModelSerializer):
    subject = serializers.SlugRelatedField(slug_field="code", read_only=True)
    exam = serializers.SerializerMethodField(help_text="Examen visé : BEPC (collège) ou BAC (lycée).")

    class Meta:
        model = Exercise
        fields = [
            "id", "title", "subject", "chapter", "level", "exam",
            "generation_status", "error_message", "created_at",
        ]
        read_only_fields = fields

    def get_exam(self, obj) -> str:
        return exam_for(obj.level)


NULLABLE_OBJECT = {"type": "object", "additionalProperties": {}, "nullable": True}


class ExerciseDetailSerializer(ExerciseSerializer):
    content = serializers.SerializerMethodField(
        help_text=(
            "Parcours (README §6, JSON Schema dans schemas/exercise-content.schema.json) sans les champs "
            "qui donnent la réponse : activity.answer, common_mistakes, explanation, dernier indice. "
            "null tant que le parcours n'est pas prêt."
        )
    )
    current_attempt = serializers.SerializerMethodField(
        help_text="Tentative commencée et non finie à reprendre (détail : GET /api/attempts/{id}/) ; null sinon."
    )

    class Meta(ExerciseSerializer.Meta):
        fields = ExerciseSerializer.Meta.fields + ["schema_version", "content", "current_attempt"]
        read_only_fields = fields

    @extend_schema_field(NULLABLE_OBJECT)
    def get_content(self, obj):
        if obj.generation_status != Exercise.GenerationStatus.READY:
            return None
        return public_content(obj.content)

    def get_current_attempt(self, obj) -> UUID | None:
        request = self.context.get("request")
        # Sans requête : V1, un parcours n'est visible que par son propriétaire.
        attempt = resumable_attempt(request.user if request else obj.owner, obj)
        return str(attempt.id) if attempt else None


class ExerciseOfflineSerializer(ExerciseDetailSerializer):
    @extend_schema_field(NULLABLE_OBJECT)
    def get_content(self, obj):
        if obj.generation_status != Exercise.GenerationStatus.READY:
            return None
        return obj.content
