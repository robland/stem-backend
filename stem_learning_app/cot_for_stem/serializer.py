from rest_framework import serializers
from .models import *


class UploadDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        exclude = ["uploaded_at", "id", "file_hash", "file_size", "original_filename"]


class SubjectSerializer(serializers.ModelSerializer):
    chapters = serializers.StringRelatedField(many=True)

    class Meta:
        model = Subject
        fields = ["id", "name", "chapters"]


class ChapterSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source="subject",
        write_only=True
    )

    class Meta:
        model = Chapter
        fields = ["id", "name", "subject", "subject_id"]


class SolvedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solved
        fields = '__all__'


class ExerciseSerializer(serializers.ModelSerializer):
    chapter = ChapterSerializer(read_only=True)
    solved = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = ["id", "title", "chapter", "solved", "statement", "level", "raw_text"]

    def get_solved(self, obj):

        request = self.context.get('request')
        if request is None:
            return None

        user = request.user
        if not user.is_authenticated:
            return None

        solved = obj.progress.filter(student=user).first()

        if not solved:
            return {
                "state": "not_started",
                "score": 0
            }
        return {
            "state": solved.state,
            "score": solved.score,
            "current_step": solved.current_step
        }


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = ["id", "objective", "explanation", "qcm"]


class QCMSerializer(serializers.ModelSerializer):
    class Meta:
        model = QCM
        fields = "__all__"
