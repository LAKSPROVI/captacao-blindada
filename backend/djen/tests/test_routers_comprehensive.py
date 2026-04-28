"""
Comprehensive tests for FastAPI routers and endpoints.

Tests health, dashboard, sistema, busca, and other key endpoints.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("IS_PRODUCTION", "false")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-for-testing-32!")

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

# Patch at BOTH app level and database module level so routers also get the mock
_patcher_app = patch("djen.api.app.get_database", return_value=_mock_db)
_patcher_db = patch("djen.api.database.get_database", return_value=_mock_db)
_patcher_sched = patch("djen.api.app.start_scheduler")

_patcher_app.start()
_patcher_db.start()
_patcher_sched.start()

from djen.api.app import app

client = TestClient(app)


def _get_token():
    from djen.api.auth import create_access_token, _clear_attempts
    from datetime import timedelta
    _clear_attempts("admin")
    return create_access_token(
        data={"sub": "admin", "role": "master"},
        expires_delta=timedelta(minutes=30),
    )


def _headers():
    return {"Authorization": f"Bearer {_get_token()}"}


# =========================================================================
# Health endpoint
# =========================================================================

class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/api/metrics/health")
        assert resp.status_code == 200

    def test_health_has_status(self):
        resp = client.get("/api/metrics/health")
        data = resp.json()
        assert "status" in data

    def test_health_no_auth_required(self):
        resp = client.get("/api/metrics/health")
        assert resp.status_code == 200


# =========================================================================
# Root endpoint
# =========================================================================

class TestRootEndpoint:
    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_has_nome(self):
        data = client.get("/").json()
        assert "nome" in data

    def test_root_has_versao(self):
        data = client.get("/").json()
        assert "versao" in data

    def test_root_has_fontes(self):
        data = client.get("/").json()
        assert "fontes_disponiveis" in data
        assert isinstance(data["fontes_disponiveis"], list)

    def test_root_has_docs_url(self):
        data = client.get("/").json()
        assert data.get("docs_url") == "/docs"

    def test_root_has_health_url(self):
        data = client.get("/").json()
        assert "health_url" in data


# =========================================================================
# Docs endpoint
# =========================================================================

class TestDocsEndpoint:
    def test_docs_returns_200(self):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert "info" in data
