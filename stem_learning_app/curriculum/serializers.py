from rest_framework import serializers

from .models import Subject, Chapter


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["code", "name"]


class ChapterSerializer(serializers.ModelSerializer):
    subject = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "subject", "level", "name", "order"]
