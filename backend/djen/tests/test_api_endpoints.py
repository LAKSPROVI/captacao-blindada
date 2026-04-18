"""
Comprehensive tests for the Captacao Peticao Blindada FastAPI endpoints.

Uses TestClient to test endpoints without needing a running server.
External network calls (DataJud, DJEN) are avoided or mocked.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Patch the scheduler and database before importing the app to avoid
# side effects during test collection (e.g. APScheduler starting,
# SQLite files being created in production paths).

_mock_db = MagicMock()
_mock_db.listar_monitorados.return_value = []
_mock_db.obter_stats.return_value = {
    "total_monitorados": 0,
    "monitorados_ativos": 0,
    "total_publicacoes": 0,
    "publicacoes_hoje": 0,
    "publicacoes_semana": 0,
    "total_buscas": 0,
    "fontes_ativas": 0,
    "ultima_busca": None,
}
_mock_db.buscar_publicacoes.return_value = []
_mock_db.conn = MagicMock()
_mock_db.conn.execute.return_value = MagicMock()


# Patch get_database globally so the lifespan and routers use our mock
with patch("djen.api.app.get_database", return_value=_mock_db), \
     patch("djen.api.app.start_scheduler"):
    from djen.api.app import app

client = TestClient(app)


# =========================================================================
# Helpers
# =========================================================================

def get_auth_token(username: str = "admin", password: str = "admin") -> str:
    """Login and return a bearer token."""
    resp = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str | None = None) -> dict:
    """Return Authorization header dict."""
    if token is None:
        token = get_auth_token()
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# 1. Root & Info
# =========================================================================


class TestRootAndInfo:
    def test_root_returns_api_info(self):
        """GET / returns API info with correct fields."""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nome"] == "Captacao Peticao Blindada"
        assert data["versao"] == "1.0.0"
        assert "fontes_disponiveis" in data
        assert isinstance(data["fontes_disponiveis"], list)
        assert "datajud" in data["fontes_disponiveis"]
        assert data["docs_url"] == "/docs"
        assert data["health_url"] == "/api/health"

    def test_docs_returns_200(self):
        """GET /docs returns 200 (Swagger UI)."""
        resp = client.get("/docs")
        assert resp.status_code == 200


# =========================================================================
# 2. Auth Endpoints
# =========================================================================


class TestAuth:
    def test_login_valid_credentials(self):
        """POST /api/auth/login with valid credentials returns token."""
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_login_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials returns 401."""
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert "detail" in resp.json()

    def test_login_nonexistent_user(self):
        """POST /api/auth/login with nonexistent user returns 401."""
        resp = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "whatever"},
        )
        assert resp.status_code == 401

    def test_me_with_valid_token(self):
        """GET /api/auth/me with valid token returns user info."""
        token = get_auth_token()
        resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert "full_name" in data
        assert data["role"] == "admin"

    def test_me_without_token(self):
        """GET /api/auth/me without token returns 401."""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self):
        """GET /api/auth/me with invalid token returns 401."""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_refresh_with_valid_token(self):
        """POST /api/auth/refresh with valid token returns new token."""
        token = get_auth_token()
        resp = client.post("/api/auth/refresh", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # The new token should be different (different exp timestamp)
        assert "expires_in" in data

    def test_refresh_without_token(self):
        """POST /api/auth/refresh without token returns 401."""
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_login_missing_fields_returns_422(self):
        """POST /api/auth/login with missing fields returns 422."""
        resp = client.post("/api/auth/login", data={})
        assert resp.status_code == 422

    def test_login_response_structure(self):
        """Token response model has correct structure."""
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        data = resp.json()
        expected_keys = {"access_token", "token_type", "expires_in"}
        assert expected_keys == set(data.keys())


# =========================================================================
# 3. Monitor Endpoints
# =========================================================================


class TestMonitor:
    def test_add_monitor(self):
        """POST /api/monitor/add creates a monitor."""
        _mock_db.adicionar_monitorado.return_value = 1
        _mock_db.obter_monitorado.return_value = {
            "id": 1,
            "tipo": "oab",
            "valor": "123456/SP",
            "nome_amigavel": "Dr. Teste",
            "ativo": True,
            "tribunal": None,
            "fontes": "datajud,djen_api",
            "criado_em": "2024-01-01 00:00:00",
            "ultima_busca": None,
            "total_publicacoes": 0,
        }

        resp = client.post(
            "/api/monitor/add",
            json={
                "tipo": "oab",
                "valor": "123456/SP",
                "nome_amigavel": "Dr. Teste",
                "fontes": ["datajud", "djen_api"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["tipo"] == "oab"
        assert data["valor"] == "123456/SP"
        assert data["nome_amigavel"] == "Dr. Teste"
        assert data["ativo"] is True

    def test_list_monitors(self):
        """GET /api/monitor/list returns monitors."""
        _mock_db.listar_monitorados.return_value = [
            {
                "id": 1,
                "tipo": "oab",
                "valor": "123456/SP",
                "nome_amigavel": "Dr. Teste",
                "ativo": True,
                "tribunal": None,
                "fontes": "datajud,djen_api",
                "criado_em": "2024-01-01 00:00:00",
                "ultima_busca": None,
                "total_publicacoes": 0,
            }
        ]

        resp = client.get("/api/monitor/list")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["tipo"] == "oab"

    def test_stats(self):
        """GET /api/monitor/stats returns stats."""
        _mock_db.obter_stats.return_value = {
            "total_monitorados": 5,
            "monitorados_ativos": 3,
            "total_publicacoes": 100,
            "publicacoes_hoje": 2,
            "publicacoes_semana": 15,
            "total_buscas": 50,
            "fontes_ativas": 2,
            "ultima_busca": "2024-06-01 12:00:00",
        }

        resp = client.get("/api/monitor/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_monitorados" in data
        assert "monitorados_ativos" in data
        assert "total_publicacoes" in data
        assert "publicacoes_hoje" in data
        assert "total_buscas" in data
        assert "fontes_ativas" in data
        assert isinstance(data["total_monitorados"], int)


# =========================================================================
# 4. Processo Endpoints
# =========================================================================


class TestProcesso:
    def test_list_agents(self):
        """GET /api/processo/agents returns list of agents."""
        resp = client.get("/api/processo/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "total" in data
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_cache_stats(self):
        """GET /api/processo/cache/stats returns cache info."""
        resp = client.get("/api/processo/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "cache" in data

    def test_clear_cache(self):
        """DELETE /api/processo/cache clears cache."""
        resp = client.delete("/api/processo/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "message" in data

    def test_resultados_returns_list(self):
        """GET /api/processo/resultados returns stored results (may be empty)."""
        resp = client.get("/api/processo/resultados")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"


# =========================================================================
# 5. Schema Validation
# =========================================================================


class TestSchemaValidation:
    def test_login_missing_username_returns_422(self):
        """POST /api/auth/login with only password returns 422."""
        resp = client.post(
            "/api/auth/login",
            data={"password": "admin"},
        )
        assert resp.status_code == 422

    def test_monitor_add_missing_required_fields_returns_422(self):
        """POST /api/monitor/add with missing required fields returns 422."""
        resp = client.post("/api/monitor/add", json={})
        assert resp.status_code == 422

    def test_monitor_add_invalid_tipo_returns_422(self):
        """POST /api/monitor/add with invalid tipo returns 422."""
        resp = client.post(
            "/api/monitor/add",
            json={"tipo": "invalid_type", "valor": "test"},
        )
        assert resp.status_code == 422

    def test_api_info_response_structure(self):
        """Root response has correct APIInfoResponse structure."""
        resp = client.get("/")
        data = resp.json()
        required_fields = {"nome", "versao", "descricao", "fontes_disponiveis", "docs_url", "health_url"}
        assert required_fields.issubset(set(data.keys()))

    def test_user_public_response_structure(self):
        """UserPublic response from /me has correct structure."""
        token = get_auth_token()
        resp = client.get("/api/auth/me", headers=auth_headers(token))
        data = resp.json()
        expected = {"username", "full_name", "role"}
        assert expected == set(data.keys())
