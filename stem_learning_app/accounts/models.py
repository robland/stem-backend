import re

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from curriculum.choices import Level


def normalize_phone(phone):
    return re.sub(r"[\s.-]", "", phone or "")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        if not extra_fields.get("pseudo"):
            raise ValueError("Le pseudo est obligatoire.")
        user = self.model(phone=normalize_phone(phone), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(phone, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Seule donnée personnelle : le téléphone (identifiant de connexion).
    Le pseudo est affiché aux autres élèves et ne doit pas permettre d'identifier l'élève.
    """

    phone = models.CharField(max_length=16, unique=True)
    pseudo = models.CharField(max_length=30, unique=True)
    level = models.CharField(max_length=4, choices=Level.choices, blank=True)
    # Série du lycée (A, C, D…) — liste exacte à confirmer, d'où un champ libre.
    serie = models.CharField(max_length=10, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["pseudo"]

    objects = UserManager()

    def __str__(self):
        return self.pseudo
