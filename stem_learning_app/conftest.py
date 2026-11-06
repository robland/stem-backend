import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser

PASSWORD = "Mot-de-passe-solide-42"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(username="eleve", phone="+242061234567", password=PASSWORD)


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_superuser(username="admin", password=PASSWORD, phone="+242069999999")


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
