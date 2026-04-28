"""
Integration tests against live Contabo deployment.

These tests verify the production deployment is working correctly.
Run with: pytest backend/djen/tests/test_integration_live.py -v
"""

import os
import pytest
import requests

LIVE_URL = os.environ.get("LIVE_URL", "https://captacaoblindada.com.br")
LIVE_ADMIN_USER = os.environ.get("LIVE_ADMIN_USER", "admin")
LIVE_ADMIN_PASS = os.environ.get("LIVE_ADMIN_PASS", "")

# Skip all tests if no password configured
pytestmark = pytest.mark.skipif(
    not LIVE_ADMIN_PASS,
    reason="LIVE_ADMIN_PASS not set - skipping live integration tests"
)


def _session():
    s = requests.Session()
    s.verify = True
    s.timeout = 15
    return s


def _login(session):
    resp = session.post(f"{LIVE_URL}/api/auth/login", data={
        "username": LIVE_ADMIN_USER,
        "password": LIVE_ADMIN_PASS,
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    session.headers["Authorization"] = f"Bearer {token}"
    return session


# =========================================================================
# Health & Connectivity
# =========================================================================

class TestLiveHealth:
    def test_health_endpoint(self):
        resp = requests.get(f"{LIVE_URL}/api/metrics/health", timeout=10)
        assert resp.status_code == 200

    def test_root_endpoint(self):
        resp = requests.get(f"{LIVE_URL}/", timeout=10)
        assert resp.status_code == 200

    def test_https_redirect(self):
        http_url = LIVE_URL.replace("https://", "http://")
        resp = requests.get(http_url, timeout=10, allow_redirects=False)
        assert resp.status_code in (301, 302, 308)

    def test_frontend_loads(self):
        resp = requests.get(f"{LIVE_URL}/login", timeout=10)
        assert resp.status_code == 200


# =========================================================================
# Auth Flow
# =========================================================================

class TestLiveAuth:
    def test_login_success(self):
        s = _session()
        resp = s.post(f"{LIVE_URL}/api/auth/login", data={
            "username": LIVE_ADMIN_USER,
            "password": LIVE_ADMIN_PASS,
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self):
        s = _session()
        resp = s.post(f"{LIVE_URL}/api/auth/login", data={
            "username": LIVE_ADMIN_USER,
            "password": "wrong_password_12345",
        })
        assert resp.status_code == 401

    def test_me_endpoint(self):
        s = _login(_session())
        resp = s.get(f"{LIVE_URL}/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == LIVE_ADMIN_USER

    def test_refresh_token(self):
        s = _login(_session())
        resp = s.post(f"{LIVE_URL}/api/auth/refresh")
        assert resp.status_code == 200
        assert "access_token" in resp.json()


# =========================================================================
# API Endpoints
# =========================================================================

class TestLiveAPI:
    def test_monitor_list(self):
        s = _login(_session())
        resp = s.get(f"{LIVE_URL}/api/monitor/list")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_monitor_stats(self):
        s = _login(_session())
        resp = s.get(f"{LIVE_URL}/api/monitor/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_monitorados" in data

    def test_processo_agents(self):
        s = _login(_session())
        resp = s.get(f"{LIVE_URL}/api/processo/agents")
        assert resp.status_code == 200

    def test_docs_accessible(self):
        resp = requests.get(f"{LIVE_URL}/docs", timeout=10)
        assert resp.status_code == 200


# =========================================================================
# Security Headers
# =========================================================================

class TestLiveSecurityHeaders:
    def test_hsts_header(self):
        resp = requests.get(f"{LIVE_URL}/api/metrics/health", timeout=10)
        assert "strict-transport-security" in resp.headers

    def test_x_content_type_options(self):
        resp = requests.get(f"{LIVE_URL}/api/metrics/health", timeout=10)
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self):
        resp = requests.get(f"{LIVE_URL}/api/metrics/health", timeout=10)
        assert "x-frame-options" in resp.headers
