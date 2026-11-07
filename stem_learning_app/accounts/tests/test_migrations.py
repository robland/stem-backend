import importlib

import pytest
from django.apps import apps

from accounts.models import User

pytestmark = pytest.mark.django_db

phone_e164 = importlib.import_module("accounts.migrations.0002_phone_e164_serie_choices")


def create(phone, pseudo, serie=""):
    # Écriture directe : contourne la normalisation, comme les comptes créés avant la migration.
    return User.objects.bulk_create([User(phone=phone, pseudo=pseudo, serie=serie)])[0]


def test_existing_phones_become_international_and_unknown_series_are_cleared():
    national = create("061112233", "a", serie="C")
    duplicate = create("+242061112233", "b")
    other = create("055556677", "c", serie="Bac pro")

    phone_e164.normalize_existing(apps, None)

    phones = {u.pseudo: (u.phone, u.serie) for u in User.objects.filter(id__in=[national.id, duplicate.id, other.id])}
    # Numéro déjà pris au format international : l'ancien compte garde son écriture (aucune fusion).
    assert phones == {"a": ("061112233", "C"), "b": ("+242061112233", ""), "c": ("+242055556677", "")}
