from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from pydantic import TypeAdapter, ValidationError as PydanticValidationError
from rest_framework import serializers

from curriculum.models import Chapter, Subject
from llm.schemas.extraction import ExerciseStatement

from .models import ExtractedExercise, Upload

statement_adapter = TypeAdapter(ExerciseStatement)


class ExtractedExerciseSerializer(serializers.ModelSerializer):
    subject = serializers.SlugRelatedField(
        slug_field="code", queryset=Subject.objects.all(), allow_null=True, required=False
    )
    chapter = serializers.PrimaryKeyRelatedField(
        queryset=Chapter.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = ExtractedExercise
        fields = ["id", "order", "statement", "subject", "chapter", "chapter_hint", "level", "validated_at"]
        read_only_fields = ["id", "order", "chapter_hint", "validated_at"]

    def validate_statement(self, value):
        try:
            return statement_adapter.validate_python(value)
        except PydanticValidationError as e:
            raise serializers.ValidationError([err["msg"].removeprefix("Value error, ") for err in e.errors()])

    def validate(self, attrs):
        if self.instance and self.instance.validated_at:
            raise serializers.ValidationError("Énoncé déjà validé : il ne peut plus être modifié.")

        # Changer de matière ou de niveau sans préciser de chapitre retire l'ancien.
        if "chapter" not in attrs and any(
            field in attrs and attrs[field] != getattr(self.instance, field) for field in ("subject", "level")
        ):
            attrs["chapter"] = None

        subject = attrs.get("subject", self.instance.subject)
        level = attrs.get("level", self.instance.level)
        chapter = attrs.get("chapter", self.instance.chapter)
        if chapter and (chapter.subject_id != getattr(subject, "id", None) or chapter.level != level):
            raise serializers.ValidationError({"chapter": "Ce chapitre ne correspond pas à la matière et au niveau."})
        return attrs


class UploadSerializer(serializers.ModelSerializer):
    exercises = ExtractedExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = Upload
        fields = ["id", "file_type", "status", "error_message", "created_at", "exercises"]
        read_only_fields = fields


@extend_schema_field(OpenApiTypes.BINARY)
class UploadFileField(serializers.FileField):
    """Fichier envoyé en multipart (sans ce typage, le schéma l'annonce comme une URL)."""


class UploadCreateSerializer(serializers.Serializer):
    file = UploadFileField(help_text="Photo (JPEG, PNG, WebP) ou PDF.")

    def validate_file(self, value):
        if value.size > settings.UPLOAD_MAX_BYTES:
            limit = settings.UPLOAD_MAX_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f"Fichier trop lourd : {limit} Mo maximum.")
        return value
