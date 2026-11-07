import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from conftest import PASSWORD

pytestmark = pytest.mark.django_db

COOKIE = settings.REFRESH_COOKIE_NAME


def login(client, user):
    return client.post(reverse("login"), {"phone": user.phone, "password": PASSWORD}, format="json")


class TestRegister:
    def test_creates_user_with_phone_pseudo_and_level(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242 06 111 22 33", "pseudo": "kimpa", "password": PASSWORD, "level": "Tle", "serie": "C"},
            format="json",
        )

        assert response.status_code == 201
        assert "password" not in response.data
        user = User.objects.get(pseudo="kimpa")
        assert user.phone == "+242061112233"
        assert (user.level, user.serie) == ("Tle", "C")
        assert user.check_password(PASSWORD)

    def test_requires_level(self, api_client):
        response = api_client.post(
            reverse("register"), {"phone": "+242061112233", "pseudo": "kimpa", "password": PASSWORD}, format="json"
        )

        assert response.status_code == 400
        assert "level" in response.data

    def test_rejects_unknown_level(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242061112233", "pseudo": "kimpa", "password": PASSWORD, "level": "CM2"},
            format="json",
        )

        assert response.status_code == 400
        assert "level" in response.data

    def test_rejects_duplicate_pseudo(self, api_client, user):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242061112233", "pseudo": user.pseudo, "password": PASSWORD, "level": "3e"},
            format="json",
        )

        assert response.status_code == 400
        assert "pseudo" in response.data

    @pytest.mark.parametrize("phone", ["abc", "123", "+24206123456789012"])
    def test_rejects_invalid_phone(self, api_client, phone):
        response = api_client.post(
            reverse("register"), {"phone": phone, "pseudo": "kimpa", "password": PASSWORD, "level": "3e"}, format="json"
        )

        assert response.status_code == 400
        assert "phone" in response.data

    @pytest.mark.parametrize("phone", ["+242 06 123 45 67", "06 123 45 67", "061234567", "00242061234567", "242061234567"])
    def test_rejects_duplicate_phone_after_normalization(self, api_client, user, phone):
        response = api_client.post(
            reverse("register"),
            {"phone": phone, "pseudo": "autre", "password": PASSWORD, "level": "3e"},
            format="json",
        )

        assert response.status_code == 400
        assert "phone" in response.data

    def test_national_number_is_stored_in_international_format(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"phone": "05.555.66.77", "pseudo": "kimpa", "password": PASSWORD, "level": "3e"},
            format="json",
        )

        assert response.status_code == 201
        assert User.objects.get(pseudo="kimpa").phone == "+242055556677"

    def test_rejects_unknown_serie(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242061112233", "pseudo": "kimpa", "password": PASSWORD, "level": "Tle", "serie": "B"},
            format="json",
        )

        assert response.status_code == 400
        assert "serie" in response.data

    def test_rejects_weak_password(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"phone": "+242061112233", "pseudo": "kimpa", "password": "1234", "level": "3e"},
            format="json",
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

    @pytest.mark.parametrize("phone", ["06 123 45 67", "+242 06 123 45 67", "00242061234567"])
    def test_any_writing_of_the_number_logs_in(self, api_client, user, phone):
        response = api_client.post(reverse("login"), {"phone": phone, "password": PASSWORD}, format="json")

        assert response.status_code == 200

    def test_rejects_wrong_password(self, api_client, user):
        response = api_client.post(reverse("login"), {"phone": user.phone, "password": "faux"}, format="json")

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


class TestMe:
    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("me")).status_code == 401

    def test_returns_profile(self, auth_client, user):
        response = auth_client.get(reverse("me"))

        assert response.status_code == 200
        assert response.data["pseudo"] == user.pseudo
        assert response.data["level"] == "3e"

    def test_updates_level_and_serie_but_not_phone(self, auth_client, user):
        response = auth_client.patch(
            reverse("me"), {"level": "2nde", "serie": "C", "phone": "+242060000000"}, format="json"
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert (user.level, user.serie) == ("2nde", "C")
        assert user.phone == "+242061234567"

    def test_put_is_not_allowed(self, auth_client):
        assert auth_client.put(reverse("me"), {"pseudo": "x"}, format="json").status_code == 405
