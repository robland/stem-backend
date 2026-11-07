import re

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from curriculum.choices import Level, Serie


def normalize_phone(phone):
    """Format international (E.164) : `06 123 45 67`, `00242…` et `242…` deviennent `+242061234567`."""
    phone = re.sub(r"[\s.()-]", "", phone or "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    elif re.fullmatch(r"0\d{8}", phone):  # numéro national congolais : 9 chiffres, le 0 est conservé
        phone = "+242" + phone
    elif re.fullmatch(r"242\d{9}", phone):
        phone = "+" + phone
    return phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, phone):
        # Connexion : le numéro saisi peut être au format national ou avec espaces.
        return super().get_by_natural_key(normalize_phone(phone))

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
    serie = models.CharField(max_length=10, choices=Serie.choices, blank=True)  # lycée uniquement

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["pseudo"]

    objects = UserManager()

    def __str__(self):
        return self.pseudo
