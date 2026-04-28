"""
Comprehensive tests for djen.api.ratelimit module.

Tests rate limiter configuration, IP extraction, and limit parsing.
"""

import pytest
from unittest.mock import MagicMock
from starlette.requests import Request
from starlette.datastructures import Headers

from djen.api.ratelimit import (
    get_client_ip,
    get_user_identifier,
    get_rate_limit_headers,
    parse_limit,
    RATE_LIMITS,
    TRUSTED_PROXIES,
    limiter,
    get_limiter,
)


# =========================================================================
# Helpers
# =========================================================================

def _make_request(client_host="192.168.1.1", headers=None):
    """Create a mock Request."""
    req = MagicMock(spec=Request)
    req.client = MagicMock()
    req.client.host = client_host
    req.headers = Headers(headers or {})
    req.state = MagicMock()
    req.state.user = None
    return req


# =========================================================================
# get_client_ip
# =========================================================================

class TestGetClientIP:
    def test_direct_client_ip(self):
        req = _make_request("10.0.0.1")
        ip = get_client_ip(req)
        assert ip == "10.0.0.1"

    def test_trusted_proxy_uses_forwarded_for(self):
        req = _make_request("127.0.0.1", {"X-Forwarded-For": "203.0.113.50, 70.41.3.18"})
        ip = get_client_ip(req)
        assert ip == "203.0.113.50"

    def test_trusted_proxy_uses_real_ip(self):
        req = _make_request("127.0.0.1", {"X-Real-IP": "203.0.113.99"})
        ip = get_client_ip(req)
        assert ip == "203.0.113.99"

    def test_untrusted_proxy_ignores_forwarded(self):
        req = _make_request("10.0.0.1", {"X-Forwarded-For": "spoofed.ip"})
        ip = get_client_ip(req)
        assert ip == "10.0.0.1"

    def test_forwarded_for_priority_over_real_ip(self):
        req = _make_request("127.0.0.1", {
            "X-Forwarded-For": "1.2.3.4",
            "X-Real-IP": "5.6.7.8",
        })
        ip = get_client_ip(req)
        assert ip == "1.2.3.4"


# =========================================================================
# get_user_identifier
# =========================================================================

class TestGetUserIdentifier:
    def test_anonymous_user_returns_ip(self):
        req = _make_request("10.0.0.1")
        req.state.user = None
        ident = get_user_identifier(req)
        assert ident.startswith("ip:")

    def test_authenticated_user_returns_user_id(self):
        req = _make_request("10.0.0.1")
        user = MagicMock()
        user.id = 42
        req.state.user = user
        ident = get_user_identifier(req)
        assert ident == "user:42"


# =========================================================================
# get_rate_limit_headers
# =========================================================================

class TestRateLimitHeaders:
    def test_returns_correct_headers(self):
        headers = get_rate_limit_headers(100, 95, 1620000000)
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "95"
        assert headers["X-RateLimit-Reset"] == "1620000000"

    def test_zero_remaining(self):
        headers = get_rate_limit_headers(10, 0, 0)
        assert headers["X-RateLimit-Remaining"] == "0"


# =========================================================================
# parse_limit
# =========================================================================

class TestParseLimit:
    def test_per_minute(self):
        count, seconds = parse_limit("30/minute")
        assert count == 30
        assert seconds == 60

    def test_per_second(self):
        count, seconds = parse_limit("5/second")
        assert count == 5
        assert seconds == 1

    def test_per_hour(self):
        count, seconds = parse_limit("100/hour")
        assert count == 100
        assert seconds == 3600

    def test_per_day(self):
        count, seconds = parse_limit("1000/day")
        assert count == 1000
        assert seconds == 86400

    def test_invalid_format(self):
        count, seconds = parse_limit("invalid")
        assert count == 60
        assert seconds == 60


# =========================================================================
# RATE_LIMITS configuration
# =========================================================================

class TestRateLimitsConfig:
    def test_auth_login_limit_exists(self):
        assert "auth_login" in RATE_LIMITS
        assert "5/minute" == RATE_LIMITS["auth_login"]

    def test_default_limit_exists(self):
        assert "default" in RATE_LIMITS

    def test_all_limits_parseable(self):
        for name, limit_str in RATE_LIMITS.items():
            count, seconds = parse_limit(limit_str)
            assert count > 0, f"Limit {name} has invalid count"
            assert seconds > 0, f"Limit {name} has invalid seconds"

    def test_auth_more_restrictive_than_default(self):
        auth_count, _ = parse_limit(RATE_LIMITS["auth_login"])
        default_count, _ = parse_limit(RATE_LIMITS["default"])
        assert auth_count < default_count

    def test_ai_endpoints_limited(self):
        assert "ai" in RATE_LIMITS

    def test_websocket_limited(self):
        assert "websocket" in RATE_LIMITS


# =========================================================================
# Limiter singleton
# =========================================================================

class TestLimiterSingleton:
    def test_get_limiter_returns_instance(self):
        l = get_limiter()
        assert l is limiter

    def test_limiter_has_default_limits(self):
        assert limiter._default_limits is not None
