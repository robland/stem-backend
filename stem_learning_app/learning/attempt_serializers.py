from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .attempts import StepStatus, current_step_id, step_states
from .models import Attempt

MAX_SYNC_ATTEMPTS = 50
MAX_SYNC_ANSWERS = 100


class StepStateSerializer(serializers.Serializer):
    step_id = serializers.CharField()
    status = serializers.ChoiceField(choices=[StepStatus.PENDING, StepStatus.SUCCEEDED, StepStatus.FAILED])
    wrong_answers = serializers.IntegerField()
    hints_used = serializers.IntegerField()
    score = serializers.IntegerField(help_text="Sur 100 : 100 − 20 par indice − 20 par erreur ; 0 si échouée.")


class AttemptSerializer(serializers.ModelSerializer):
    current_step_id = serializers.SerializerMethodField(help_text="Étape à traiter ; null si la tentative est finie.")
    steps = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = [
            "id", "exercise", "mode", "started_at", "finished_at", "score", "hints_used",
            "current_step_id", "steps",
        ]
        read_only_fields = fields

    def _states(self, obj):
        if not hasattr(obj, "_step_states"):
            obj._step_states = step_states(obj)
        return obj._step_states

    def get_current_step_id(self, obj) -> str | None:
        return current_step_id(self._states(obj))

    @extend_schema_field(StepStateSerializer(many=True))
    def get_steps(self, obj):
        return StepStateSerializer(self._states(obj), many=True).data


class AttemptStartSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, help_text="Généré par le client (hors-ligne) : rend l'appel idempotent.")
    started_at = serializers.DateTimeField(required=False)


def _validate_response(value):
    if not isinstance(value, dict):
        raise serializers.ValidationError("La réponse doit être un objet JSON (cf. README §5.1).")
    return value


class AnswerCreateSerializer(serializers.Serializer):
    step_id = serializers.CharField(max_length=20)
    response = serializers.JSONField(help_text="Format selon le type d'activité (README §5.1).")
    client_uuid = serializers.UUIDField(help_text="Généré par le client : un renvoi ne crée pas de doublon.")
    answered_at = serializers.DateTimeField(required=False)
    hints_used = serializers.IntegerField(
        required=False, min_value=0, max_value=3, help_text="Indices consultés hors-ligne pour cette étape."
    )

    def validate_response(self, value):
        return _validate_response(value)


class AnswerResultSerializer(serializers.Serializer):
    is_correct = serializers.BooleanField()
    feedback = serializers.CharField(allow_null=True)
    details = serializers.DictField(help_text="Détail par élément (trous, points, paires…).")
    step = StepStateSerializer()
    explanation = serializers.CharField(allow_null=True, help_text="Correction rédigée, une fois l'étape close.")
    attempt = AttemptSerializer()


class HintRequestSerializer(serializers.Serializer):
    step_id = serializers.CharField(max_length=20)


class HintSerializer(serializers.Serializer):
    step_id = serializers.CharField()
    hint = serializers.CharField()
    level = serializers.IntegerField()
    total = serializers.IntegerField()


# --- Synchronisation hors-ligne ---------------------------------------------------------

class SyncAnswerSerializer(AnswerCreateSerializer):
    answered_at = serializers.DateTimeField()


class SyncAttemptSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    exercise = serializers.UUIDField()
    started_at = serializers.DateTimeField()
    answers = SyncAnswerSerializer(many=True, max_length=MAX_SYNC_ANSWERS)


class SyncRequestSerializer(serializers.Serializer):
    attempts = SyncAttemptSerializer(many=True, max_length=MAX_SYNC_ATTEMPTS)


class SyncAnswerResultSerializer(serializers.Serializer):
    client_uuid = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["accepted", "duplicate", "rejected"])
    is_correct = serializers.BooleanField(allow_null=True)
    reason = serializers.CharField(allow_null=True)


class SyncAttemptResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["synced", "rejected"])
    reason = serializers.CharField(allow_null=True)
    attempt = AttemptSerializer(allow_null=True)
    answers = SyncAnswerResultSerializer(many=True)


class SyncResultSerializer(serializers.Serializer):
    attempts = SyncAttemptResultSerializer(many=True)
