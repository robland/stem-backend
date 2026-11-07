from rest_framework import serializers

from curriculum.serializers import ChapterSerializer

from .models import Mastery
from .serializers import ExerciseSerializer


class SummarySerializer(serializers.Serializer):
    exercises_done = serializers.IntegerField(help_text="Parcours terminés au moins une fois.")
    attempts_finished = serializers.IntegerField()
    average_score = serializers.IntegerField(allow_null=True)
    streak_days = serializers.IntegerField(help_text="Jours consécutifs d'activité, jusqu'à aujourd'hui ou hier.")
    author_points = serializers.IntegerField(help_text="Points gagnés avec mes défis (README §5.4).")


class SubjectProgressSerializer(serializers.Serializer):
    subject = serializers.CharField()
    exercises_done = serializers.IntegerField()
    average_score = serializers.IntegerField()


class MasterySerializer(serializers.ModelSerializer):
    chapter = ChapterSerializer()

    class Meta:
        model = Mastery
        fields = ["chapter", "score", "state", "next_review_at", "updated_at"]


class ReviewItemSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=["to_finish", "to_review"], help_text="to_finish : tentative commencée ; to_review : révision échue."
    )
    exercise = ExerciseSerializer()
    attempt = serializers.UUIDField(allow_null=True, help_text="Tentative à reprendre (to_finish).")
    due_at = serializers.DateTimeField()
    last_score = serializers.IntegerField(allow_null=True)


class ProgressSerializer(serializers.Serializer):
    summary = SummarySerializer()
    subjects = SubjectProgressSerializer(many=True)
    chapters = MasterySerializer(many=True)
    review_today = ReviewItemSerializer(many=True, help_text="« Révision du jour » : 10 parcours au plus.")
