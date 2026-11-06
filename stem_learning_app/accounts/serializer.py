import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User, normalize_phone

PHONE_RE = re.compile(r"^\+?[0-9]{8,15}$")


class RegisterSerializer(serializers.ModelSerializer):
    """Seule donnée personnelle collectée : le téléphone. `pseudo` est un nom d'affichage."""

    password = serializers.CharField(allow_blank=False, write_only=True)

    class Meta:
        model = User
        fields = ['phone', 'pseudo', 'password', 'level', 'serie']
        extra_kwargs = {
            # La normalisation précède le contrôle d'unicité (cf. validate_phone).
            # La saisie peut contenir espaces/points/tirets, d'où une longueur plus large que le champ.
            'phone': {'validators': [], 'max_length': 25},
            'level': {'required': True, 'allow_blank': False},
        }

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not PHONE_RE.match(phone):
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return phone

    def validate(self, attrs):
        user = User(pseudo=attrs.get("pseudo"), phone=attrs.get("phone"))
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone', 'pseudo', 'level', 'serie', 'date_joined']
        read_only_fields = ['phone', 'date_joined']
