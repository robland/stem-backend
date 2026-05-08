from rest_framework import serializers
from .models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(allow_blank=False, write_only=True)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'username', 'password']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            phone=validated_data["phone"],
            password=validated_data["password"]
        )
        return user