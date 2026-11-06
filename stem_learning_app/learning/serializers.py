from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from llm.services import exam_for

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


class ExerciseDetailSerializer(ExerciseSerializer):
    content = serializers.SerializerMethodField(
        help_text=(
            "Parcours (README §6, JSON Schema dans schemas/exercise-content.schema.json) sans les champs "
            "qui donnent la réponse : activity.answer, common_mistakes, explanation, dernier indice. "
            "null tant que le parcours n'est pas prêt."
        )
    )

    class Meta(ExerciseSerializer.Meta):
        fields = ExerciseSerializer.Meta.fields + ["schema_version", "content"]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_content(self, obj):
        if obj.generation_status != Exercise.GenerationStatus.READY:
            return None
        return public_content(obj.content)


class ExerciseOfflineSerializer(ExerciseDetailSerializer):
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_content(self, obj):
        if obj.generation_status != Exercise.GenerationStatus.READY:
            return None
        return obj.content
