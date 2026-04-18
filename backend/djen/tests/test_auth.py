"""Comprehensive tests for djen.api.auth JWT authentication module."""

import os
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from jose import jwt

# Ensure predictable defaults for testing
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("ADMIN_FULL_NAME", "Administrador")

from djen.api.auth import (
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    _users_db,
    authenticate_user,
    create_access_token,
    hash_password,
    verify_password,
    UserInDB,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client():
    """Build a fresh TestClient.

    Imported lazily so module-level env vars are set before app is touched.
    """
    from fastapi.testclient import TestClient
    from djen.api.app import app

    return TestClient(app, raise_server_exceptions=False)


def _admin_token() -> str:
    """Get a valid admin JWT."""
    return create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Password hashing & verification
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        h = hash_password("secret")
        assert isinstance(h, str)
        assert h != "secret"

    def test_verify_password_correct(self):
        h = hash_password("mypass")
        assert verify_password("mypass", h) is True

    def test_verify_password_wrong(self):
        h = hash_password("mypass")
        assert verify_password("wrong", h) is False

    def test_hash_is_unique_per_call(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


# ---------------------------------------------------------------------------
# 2. Token creation with correct claims
# ---------------------------------------------------------------------------


class TestTokenCreation:
    def test_token_contains_sub_and_role(self):
        token = create_access_token(
            data={"sub": "alice", "role": "user"},
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "alice"
        assert payload["role"] == "user"
        assert "exp" in payload

    def test_token_default_expiry(self):
        token = create_access_token(data={"sub": "bob"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload


# ---------------------------------------------------------------------------
# 3. Token expiration
# ---------------------------------------------------------------------------


class TestTokenExpiration:
    def test_expired_token_rejected(self):
        token = create_access_token(
            data={"sub": "admin", "role": "admin"},
            expires_delta=timedelta(seconds=-1),  # already expired
        )
        client = _get_client()
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Token with invalid signature rejected
# ---------------------------------------------------------------------------


class TestInvalidSignature:
    def test_bad_signature_rejected(self):
        token = jwt.encode(
            {"sub": "admin", "role": "admin", "exp": time.time() + 3600},
            "wrong-secret",
            algorithm=ALGORITHM,
        )
        client = _get_client()
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 5. User registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_new_user(self):
        client = _get_client()
        token = _admin_token()
        payload = {
            "username": "newuser_test",
            "password": "pass123",
            "full_name": "New User",
            "role": "user",
        }
        resp = client.post("/api/auth/register", json=payload, headers=_auth_header(token))
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser_test"
        assert body["role"] == "user"
        # Cleanup
        _users_db.pop("newuser_test", None)

    def test_register_duplicate_user(self):
        client = _get_client()
        token = _admin_token()
        payload = {
            "username": "dupuser",
            "password": "pass",
            "full_name": "Dup",
            "role": "user",
        }
        # Create first
        client.post("/api/auth/register", json=payload, headers=_auth_header(token))
        # Duplicate
        resp = client.post("/api/auth/register", json=payload, headers=_auth_header(token))
        assert resp.status_code == 409
        _users_db.pop("dupuser", None)

    def test_register_requires_admin_role(self):
        """A non-admin user cannot register new users."""
        # Insert a regular user
        _users_db["regularuser"] = UserInDB(
            username="regularuser",
            hashed_password=hash_password("pass"),
            full_name="Regular",
            role="user",
        )
        token = create_access_token(
            data={"sub": "regularuser", "role": "user"},
            expires_delta=timedelta(minutes=5),
        )
        client = _get_client()
        payload = {
            "username": "blocked",
            "password": "p",
            "full_name": "B",
            "role": "user",
        }
        resp = client.post("/api/auth/register", json=payload, headers=_auth_header(token))
        assert resp.status_code == 403
        _users_db.pop("regularuser", None)


# ---------------------------------------------------------------------------
# 6. Login endpoint
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    def test_login_success(self):
        client = _get_client()
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_login_invalid_password(self):
        client = _get_client()
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self):
        client = _get_client()
        resp = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "x"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 7. /api/auth/me with valid token
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    def test_me_returns_user_info(self):
        client = _get_client()
        token = _admin_token()
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "admin"
        assert body["role"] == "admin"
        assert "full_name" in body


# ---------------------------------------------------------------------------
# 8. /api/auth/me without token -> 401
# ---------------------------------------------------------------------------


class TestMeUnauthorized:
    def test_me_no_token(self):
        client = _get_client()
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 9. /api/auth/refresh endpoint
# ---------------------------------------------------------------------------


class TestRefreshEndpoint:
    def test_refresh_returns_new_token(self):
        client = _get_client()
        token = _admin_token()
        resp = client.post("/api/auth/refresh", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        # The refreshed token should be different from the original
        assert body["access_token"] != token
        assert body["token_type"] == "bearer"

    def test_refresh_without_token(self):
        client = _get_client()
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 10. Role-based access control
# ---------------------------------------------------------------------------


class TestRoleBasedAccess:
    def test_admin_can_register(self):
        client = _get_client()
        token = _admin_token()
        payload = {
            "username": "rbac_test_user",
            "password": "x",
            "full_name": "RBAC",
            "role": "viewer",
        }
        resp = client.post("/api/auth/register", json=payload, headers=_auth_header(token))
        assert resp.status_code == 201
        _users_db.pop("rbac_test_user", None)

    def test_viewer_cannot_register(self):
        _users_db["vieweruser"] = UserInDB(
            username="vieweruser",
            hashed_password=hash_password("v"),
            full_name="Viewer",
            role="viewer",
        )
        token = create_access_token(
            data={"sub": "vieweruser", "role": "viewer"},
            expires_delta=timedelta(minutes=5),
        )
        client = _get_client()
        payload = {
            "username": "nope",
            "password": "p",
            "full_name": "N",
            "role": "user",
        }
        resp = client.post("/api/auth/register", json=payload, headers=_auth_header(token))
        assert resp.status_code == 403
        _users_db.pop("vieweruser", None)


# ---------------------------------------------------------------------------
# 11. Default admin user creation from env vars
# ---------------------------------------------------------------------------


class TestDefaultAdmin:
    def test_default_admin_exists_in_db(self):
        assert "admin" in _users_db
        admin = _users_db["admin"]
        assert admin.role == "admin"
        assert admin.full_name == "Administrador"

    def test_default_admin_password_verifiable(self):
        admin = _users_db["admin"]
        assert verify_password("admin", admin.hashed_password)


# ---------------------------------------------------------------------------
# 12. Invalid credentials return 401
# ---------------------------------------------------------------------------


class TestInvalidCredentials:
    def test_authenticate_user_returns_none_for_bad_password(self):
        result = authenticate_user("admin", "badpassword")
        assert result is None

    def test_authenticate_user_returns_none_for_missing_user(self):
        result = authenticate_user("ghost", "pass")
        assert result is None

    def test_authenticate_user_success(self):
        result = authenticate_user("admin", "admin")
        assert result is not None
        assert result.username == "admin"
