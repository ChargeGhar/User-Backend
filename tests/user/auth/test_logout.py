import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.user.auth.models import User


pytestmark = pytest.mark.django_db


def _create_user(email: str, username: str) -> User:
    return User.objects.create(
        email=email,
        username=username,
        status="ACTIVE",
        is_active=True,
    )


def _auth_tokens(user: User) -> tuple[str, str]:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def _auth_client(access_token: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


class TestLogoutBehavior:
    def test_logout_same_user_valid_refresh_blacklists_token(self):
        user = _create_user("logout.same@example.com", "logout_same")
        access, refresh = _auth_tokens(user)
        client = _auth_client(access)

        response = client.post("/api/auth/logout", {"refresh_token": refresh}, format="json")
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["token_revoked"] is True
        assert body["data"]["revocation_reason"] == "valid_blacklisted"

    def test_logout_accepts_refresh_alias_field(self):
        user = _create_user("logout.alias@example.com", "logout_alias")
        access, refresh = _auth_tokens(user)
        client = _auth_client(access)

        response = client.post("/api/auth/logout", {"refresh": refresh}, format="json")
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["token_revoked"] is True
        assert body["data"]["revocation_reason"] == "valid_blacklisted"

    def test_logout_malformed_refresh_is_idempotent(self):
        user = _create_user("logout.malformed@example.com", "logout_malformed")
        access, _ = _auth_tokens(user)
        client = _auth_client(access)

        response = client.post("/api/auth/logout", {"refresh_token": "not-a-jwt"}, format="json")
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["token_revoked"] is False
        assert body["data"]["revocation_reason"] == "already_invalid"

    def test_logout_already_blacklisted_refresh_is_idempotent(self):
        user = _create_user("logout.blacklisted@example.com", "logout_blacklisted")
        access, refresh = _auth_tokens(user)
        client = _auth_client(access)

        first = client.post("/api/auth/logout", {"refresh_token": refresh}, format="json")
        second = client.post("/api/auth/logout", {"refresh_token": refresh}, format="json")

        first_body = first.json()
        second_body = second.json()

        assert first.status_code == 200
        assert first_body["data"]["token_revoked"] is True
        assert first_body["data"]["revocation_reason"] == "valid_blacklisted"

        assert second.status_code == 200
        assert second_body["success"] is True
        assert second_body["data"]["token_revoked"] is False
        assert second_body["data"]["revocation_reason"] == "already_invalid"

    def test_logout_cross_user_refresh_returns_success_with_mismatch_reason(self):
        user_a = _create_user("logout.usera@example.com", "logout_user_a")
        user_b = _create_user("logout.userb@example.com", "logout_user_b")

        _, refresh_a = _auth_tokens(user_a)
        access_b, _ = _auth_tokens(user_b)
        client = _auth_client(access_b)

        response = client.post("/api/auth/logout", {"refresh_token": refresh_a}, format="json")
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["token_revoked"] is False
        assert body["data"]["revocation_reason"] == "token_mismatch"

    def test_logout_missing_refresh_returns_success_with_token_missing(self):
        user = _create_user("logout.missing@example.com", "logout_missing")
        access, _ = _auth_tokens(user)
        client = _auth_client(access)

        response = client.post("/api/auth/logout", {}, format="json")
        body = response.json()

        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["token_revoked"] is False
        assert body["data"]["revocation_reason"] == "token_missing"


class TestRefreshRegression:
    def test_refresh_with_invalid_token_returns_400_not_500(self):
        client = APIClient()
        response = client.post("/api/auth/refresh", {"refresh": "not-a-jwt"}, format="json")
        body = response.json()

        assert response.status_code == 400
        assert body["success"] is False
        assert body["error"]["code"] == "invalid_refresh_token"
