import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import CustomUser

PHONE_RE = re.compile(r"^\+?[0-9]{8,15}$")


class RegisterSerializer(serializers.ModelSerializer):
    """Seules données personnelles collectées : le téléphone. `username` est un pseudo d'affichage."""

    password = serializers.CharField(allow_blank=False, write_only=True)

    class Meta:
        model = CustomUser
        fields = ['phone', 'username', 'password']

    def validate_phone(self, value):
        phone = re.sub(r"[\s.-]", "", value)
        if not PHONE_RE.match(phone):
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        if CustomUser.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return phone

    def validate(self, attrs):
        user = CustomUser(username=attrs.get("username"), phone=attrs.get("phone"))
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        return CustomUser.objects.create_user(
            username=validated_data["username"],
            phone=validated_data["phone"],
            password=validated_data["password"]
        )
