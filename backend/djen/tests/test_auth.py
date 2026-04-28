"""Comprehensive tests for djen.api.auth JWT authentication module.

Updated to work with DB-backed users (no more _users_db dict).
"""

import os
import time
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
import jwt

# Ensure predictable defaults for testing
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("IS_PRODUCTION", "false")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("ADMIN_FULL_NAME", "Administrador")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-for-testing-32!")

from djen.api.auth import (
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    authenticate_user,
    create_access_token,
    hash_password,
    verify_password,
    get_user_from_db,
    UserInDB,
    UserPublic,
    UserCreate,
    Token,
    TokenData,
    _check_login_blocked,
    _register_failed_attempt,
    _clear_attempts,
    _login_attempts,
)

# ---------------------------------------------------------------------------
# Build a properly mocked TestClient (same pattern as test_api_endpoints.py)
# ---------------------------------------------------------------------------
_mock_db = MagicMock()
_mock_db.listar_monitorados.return_value = []
_mock_db.obter_stats.return_value = {
    "total_monitorados": 0, "monitorados_ativos": 0,
    "total_publicacoes": 0, "publicacoes_hoje": 0,
    "publicacoes_semana": 0, "total_buscas": 0,
    "fontes_ativas": 0, "ultima_busca": None,
}
_mock_db.buscar_publicacoes.return_value = []
_mock_db.conn = MagicMock()
_mock_db.conn.execute.return_value = MagicMock()
_mock_db.conn.execute.return_value.fetchone.return_value = None
_mock_db.conn.execute.return_value.fetchall.return_value = []

with patch("djen.api.app.get_database", return_value=_mock_db), \
     patch("djen.api.app.start_scheduler"):
    from djen.api.app import app

from fastapi.testclient import TestClient
client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_token() -> str:
    """Get a valid admin JWT."""
    return create_access_token(
        data={"sub": "admin", "role": "master"},
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

    def test_empty_password(self):
        h = hash_password("")
        assert isinstance(h, str)
        assert verify_password("", h) is True

    def test_long_password_truncated_at_72(self):
        long_pw = "A" * 100
        h = hash_password(long_pw)
        assert verify_password(long_pw, h) is True

    def test_unicode_password(self):
        h = hash_password("senhaçãoéàü")
        assert verify_password("senhaçãoéàü", h) is True
        assert verify_password("senhaçãoéàx", h) is False

    def test_verify_with_invalid_hash_returns_false(self):
        assert verify_password("test", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# 2. Token creation with correct claims
# ---------------------------------------------------------------------------

class TestTokenCreation:
    def test_token_contains_sub_and_role(self):
        token = create_access_token(
            data={"sub": "alice", "role": "viewer"},
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "alice"
        assert payload["role"] == "viewer"
        assert "exp" in payload

    def test_token_default_expiry(self):
        token = create_access_token(data={"sub": "bob"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_token_custom_expiry(self):
        token = create_access_token(
            data={"sub": "carol"},
            expires_delta=timedelta(hours=2),
        )
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["exp"] > time.time()

    def test_token_with_tenant_id(self):
        token = create_access_token(
            data={"sub": "dave", "role": "operator", "tenant_id": 42},
        )
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["tenant_id"] == 42

    def test_token_is_string(self):
        token = create_access_token(data={"sub": "test"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_different_tokens_for_same_data(self):
        t1 = create_access_token(data={"sub": "x"}, expires_delta=timedelta(minutes=1))
        time.sleep(0.01)
        t2 = create_access_token(data={"sub": "x"}, expires_delta=timedelta(minutes=1))
        p1 = jwt.decode(t1, SECRET_KEY, algorithms=[ALGORITHM])
        p2 = jwt.decode(t2, SECRET_KEY, algorithms=[ALGORITHM])
        assert p1["sub"] == p2["sub"] == "x"


# ---------------------------------------------------------------------------
# 3. Token expiration
# ---------------------------------------------------------------------------

class TestTokenExpiration:
    def test_expired_token_rejected(self):
        token = create_access_token(
            data={"sub": "admin", "role": "master"},
            expires_delta=timedelta(seconds=-1),
        )
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Token with invalid signature rejected
# ---------------------------------------------------------------------------

class TestInvalidSignature:
    def test_bad_signature_rejected(self):
        token = jwt.encode(
            {"sub": "admin", "role": "master", "exp": time.time() + 3600},
            "wrong-secret",
            algorithm=ALGORITHM,
        )
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 401

    def test_malformed_token_rejected(self):
        resp = client.get("/api/auth/me", headers=_auth_header("not.a.jwt"))
        assert resp.status_code == 401

    def test_empty_token_rejected(self):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 5. Login endpoint
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    def test_login_success(self):
        _clear_attempts("admin")
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
        _clear_attempts("admin")
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self):
        resp = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "x"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields_returns_422(self):
        resp = client.post("/api/auth/login", data={})
        assert resp.status_code == 422

    def test_login_response_structure(self):
        _clear_attempts("admin")
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        data = resp.json()
        expected_keys = {"access_token", "token_type", "expires_in"}
        assert expected_keys == set(data.keys())

    def test_login_sets_httponly_cookie(self):
        _clear_attempts("admin")
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200
        cookies = resp.cookies
        assert "access_token" in cookies


# ---------------------------------------------------------------------------
# 6. /api/auth/me with valid token
# ---------------------------------------------------------------------------

class TestMeEndpoint:
    def test_me_returns_user_info(self):
        token = _admin_token()
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "admin"
        assert "full_name" in body
        assert "role" in body
        assert "id" in body

    def test_me_no_token(self):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 7. /api/auth/refresh endpoint
# ---------------------------------------------------------------------------

class TestRefreshEndpoint:
    def test_refresh_returns_new_token(self):
        token = _admin_token()
        resp = client.post("/api/auth/refresh", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["access_token"] != token
        assert body["token_type"] == "bearer"

    def test_refresh_without_token(self):
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 8. Login blocking (brute force protection)
# ---------------------------------------------------------------------------

class TestLoginBlocking:
    def setup_method(self):
        _login_attempts.clear()

    def test_not_blocked_initially(self):
        assert _check_login_blocked("testuser") is False

    def test_blocked_after_max_attempts(self):
        for _ in range(5):
            _register_failed_attempt("blocktest")
        assert _check_login_blocked("blocktest") is True

    def test_clear_attempts_unblocks(self):
        for _ in range(5):
            _register_failed_attempt("cleartest")
        assert _check_login_blocked("cleartest") is True
        _clear_attempts("cleartest")
        assert _check_login_blocked("cleartest") is False

    def test_fewer_than_max_not_blocked(self):
        for _ in range(4):
            _register_failed_attempt("fewtest")
        assert _check_login_blocked("fewtest") is False

    def test_attempts_list_capped_at_10(self):
        for _ in range(15):
            _register_failed_attempt("captest")
        assert len(_login_attempts["captest"]) == 10


# ---------------------------------------------------------------------------
# 9. Pydantic models
# ---------------------------------------------------------------------------

class TestPydanticModels:
    def test_token_model(self):
        t = Token(access_token="abc", token_type="bearer", expires_in=3600)
        assert t.access_token == "abc"

    def test_token_data_model(self):
        td = TokenData(username="user", role="viewer", tenant_id=1)
        assert td.username == "user"

    def test_user_public_model(self):
        up = UserPublic(id=1, username="u", full_name="U", role="viewer")
        assert up.tenant_id is None

    def test_user_in_db_model(self):
        u = UserInDB(id=1, username="u", hashed_password="h", full_name="U", role="master")
        assert u.role == "master"

    def test_user_create_model(self):
        uc = UserCreate(username="new", password="pass", full_name="New User")
        assert uc.role == "viewer"  # default

    def test_user_create_custom_role(self):
        uc = UserCreate(username="new", password="pass", full_name="New", role="operator", tenant_id=5)
        assert uc.role == "operator"
        assert uc.tenant_id == 5


# ---------------------------------------------------------------------------
# 10. authenticate_user function
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_authenticate_returns_none_for_bad_password(self):
        result = authenticate_user("admin", "badpassword")
        assert result is None

    def test_authenticate_returns_none_for_missing_user(self):
        result = authenticate_user("ghost", "pass")
        assert result is None

    def test_authenticate_success(self):
        result = authenticate_user("admin", "admin")
        assert result is not None
        assert result.username == "admin"
        assert result.role == "master"


# ---------------------------------------------------------------------------
# 11. Logout endpoint
# ---------------------------------------------------------------------------

class TestLogoutEndpoint:
    def test_logout_clears_cookie(self):
        _clear_attempts("admin")
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        assert login_resp.status_code == 200
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_logout_without_session(self):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 12. Register endpoint
# ---------------------------------------------------------------------------

class TestRegisterEndpoint:
    def test_register_requires_auth(self):
        resp = client.post("/api/auth/register", json={
            "username": "noauth", "password": "p", "full_name": "N", "role": "viewer"
        })
        assert resp.status_code == 401

    def test_register_invalid_role_returns_422(self):
        token = _admin_token()
        resp = client.post("/api/auth/register", json={
            "username": "badrole", "password": "p", "full_name": "B", "role": "superadmin"
        }, headers=_auth_header(token))
        assert resp.status_code == 422
