import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from llm.clients import get_client

PASSWORD = "Mot-de-passe-solide-42"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(phone="+242061234567", pseudo="eleve", password=PASSWORD, level="3e")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(phone="+242067654321", pseudo="camarade", password=PASSWORD, level="3e")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(phone="+242069999999", pseudo="admin", password=PASSWORD)


def _client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def auth_client(user):
    return _client_for(user)


@pytest.fixture
def admin_client(admin_user):
    return _client_for(admin_user)


@pytest.fixture
def fake_llm():
    """FakeLLMClient partagé (settings de test) : file de réponses vidée à chaque test."""
    client = get_client()
    client.reset()
    yield client
    client.reset()
