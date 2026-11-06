import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser
from conftest import PASSWORD

pytestmark = pytest.mark.django_db

COOKIE = settings.REFRESH_COOKIE_NAME


def login(client, user):
    return client.post(reverse("login"), {"username": user.username, "password": PASSWORD}, format="json")


class TestRegister:
    def test_creates_user_with_phone_and_pseudo_only(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242 06 111 22 33", "username": "kimpa", "password": PASSWORD},
            format="json",
        )

        assert response.status_code == 201
        assert "password" not in response.data
        user = CustomUser.objects.get(username="kimpa")
        assert user.phone == "+242061112233"
        assert user.check_password(PASSWORD)

    @pytest.mark.parametrize("phone", ["abc", "123", "+24206123456789012"])
    def test_rejects_invalid_phone(self, api_client, phone):
        response = api_client.post(
            reverse("register"), {"phone": phone, "username": "kimpa", "password": PASSWORD}, format="json"
        )

        assert response.status_code == 400
        assert "phone" in response.data

    def test_rejects_duplicate_phone_after_normalization(self, api_client, user):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242 06 123 45 67", "username": "autre", "password": PASSWORD},
            format="json",
        )

        assert response.status_code == 400
        assert "phone" in response.data

    def test_rejects_weak_password(self, api_client):
        response = api_client.post(
            reverse("register"), {"phone": "+242061112233", "username": "kimpa", "password": "1234"}, format="json"
        )

        assert response.status_code == 400
        assert "password" in response.data


class TestLogin:
    def test_returns_access_and_sets_refresh_cookie(self, api_client, user):
        response = login(api_client, user)

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" not in response.data
        cookie = response.cookies[COOKIE]
        assert cookie["httponly"]
        assert cookie["path"] == settings.REFRESH_COOKIE_PATH

    def test_rejects_wrong_password(self, api_client, user):
        response = api_client.post(reverse("login"), {"username": user.username, "password": "faux"}, format="json")

        assert response.status_code == 401


class TestRefresh:
    def test_refresh_from_cookie_rotates_cookie(self, api_client, user):
        old_refresh = login(api_client, user).cookies[COOKIE].value

        response = api_client.post(reverse("refresh"), format="json")

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" not in response.data
        assert response.cookies[COOKIE].value != old_refresh

    def test_refresh_from_body_returns_new_refresh_in_body(self, api_client, user):
        refresh = str(RefreshToken.for_user(user))

        response = api_client.post(reverse("refresh"), {"refresh": refresh}, format="json")

        assert response.status_code == 200
        assert response.data["refresh"] != refresh
        assert COOKIE not in response.cookies

    def test_rotated_refresh_is_blacklisted(self, api_client, user):
        refresh = str(RefreshToken.for_user(user))
        api_client.post(reverse("refresh"), {"refresh": refresh}, format="json")

        response = api_client.post(reverse("refresh"), {"refresh": refresh}, format="json")

        assert response.status_code == 401

    def test_without_token_is_unauthorized(self, api_client):
        response = api_client.post(reverse("refresh"), format="json")

        assert response.status_code == 401


class TestLogout:
    def test_blacklists_refresh_and_deletes_cookie(self, api_client, user):
        login(api_client, user)
        refresh = api_client.cookies[COOKIE].value

        response = api_client.post(reverse("logout"))

        assert response.status_code == 204
        assert response.cookies[COOKIE].value == ""
        reuse = api_client.post(reverse("refresh"), {"refresh": refresh}, format="json")
        assert reuse.status_code == 401

    def test_succeeds_without_token(self, api_client):
        response = api_client.post(reverse("logout"))

        assert response.status_code == 204
