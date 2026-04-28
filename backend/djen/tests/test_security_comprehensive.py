"""
Comprehensive tests for djen.api.security module.

Tests API Key management, 2FA/TOTP, and SSO configuration.
"""

import time
import pytest
from djen.api.security import (
    APIKeyManager,
    APIKey,
    TwoFactorAuth,
    SSOConfig,
    get_api_key_manager,
    get_2fa,
    get_sso_config,
)


# =========================================================================
# APIKeyManager
# =========================================================================

class TestAPIKeyManager:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_create_key_returns_api_key(self):
        key = self.mgr.create_key("Test Key")
        assert isinstance(key, APIKey)
        assert key.nome == "Test Key"
        assert key.active is True

    def test_create_key_has_sk_prefix(self):
        key = self.mgr.create_key("Test")
        assert key.key.startswith("sk_")

    def test_create_key_unique_ids(self):
        k1 = self.mgr.create_key("K1")
        k2 = self.mgr.create_key("K2")
        assert k1.id != k2.id
        assert k1.key != k2.key

    def test_create_key_with_tenant(self):
        key = self.mgr.create_key("Tenant Key", tenant_id=42)
        assert key.tenant_id == 42

    def test_create_key_with_expiry(self):
        key = self.mgr.create_key("Expiring", expires_days=30)
        assert key.expires_at is not None

    def test_create_key_without_expiry(self):
        key = self.mgr.create_key("NoExpiry")
        assert key.expires_at is None

    def test_validate_key_valid(self):
        key = self.mgr.create_key("Valid")
        result = self.mgr.validate_key(key.key)
        assert result is not None
        assert result.id == key.id

    def test_validate_key_updates_last_used(self):
        key = self.mgr.create_key("Used")
        assert key.last_used is None
        self.mgr.validate_key(key.key)
        assert key.last_used is not None

    def test_validate_key_invalid(self):
        result = self.mgr.validate_key("sk_nonexistent")
        assert result is None

    def test_validate_key_revoked(self):
        key = self.mgr.create_key("Revoked")
        self.mgr.revoke_key(key.id)
        result = self.mgr.validate_key(key.key)
        assert result is None

    def test_revoke_key_success(self):
        key = self.mgr.create_key("ToRevoke")
        assert self.mgr.revoke_key(key.id) is True
        assert key.active is False

    def test_revoke_key_nonexistent(self):
        assert self.mgr.revoke_key("nonexistent") is False

    def test_list_keys_empty(self):
        keys = self.mgr.list_keys()
        assert keys == []

    def test_list_keys_all(self):
        self.mgr.create_key("K1")
        self.mgr.create_key("K2")
        keys = self.mgr.list_keys()
        assert len(keys) == 2

    def test_list_keys_by_tenant(self):
        self.mgr.create_key("T1", tenant_id=1)
        self.mgr.create_key("T2", tenant_id=2)
        self.mgr.create_key("T1b", tenant_id=1)
        keys = self.mgr.list_keys(tenant_id=1)
        assert len(keys) == 2

    def test_list_keys_no_secret_exposed(self):
        self.mgr.create_key("Secret")
        keys = self.mgr.list_keys()
        assert "key" not in keys[0]  # key value should not be in list

    def test_list_keys_has_required_fields(self):
        self.mgr.create_key("Fields")
        keys = self.mgr.list_keys()
        k = keys[0]
        assert "id" in k
        assert "nome" in k
        assert "active" in k
        assert "created_at" in k

    def test_create_many_keys(self):
        for i in range(50):
            self.mgr.create_key(f"Key_{i}")
        keys = self.mgr.list_keys()
        assert len(keys) == 50

    def test_validate_expired_key(self):
        key = self.mgr.create_key("Expired", expires_days=-1)
        result = self.mgr.validate_key(key.key)
        assert result is None


# =========================================================================
# TwoFactorAuth
# =========================================================================

class TestTwoFactorAuth:
    def setup_method(self):
        self.tfa = TwoFactorAuth()

    def test_generate_secret_returns_string(self):
        secret = self.tfa.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) > 10

    def test_generate_secret_unique(self):
        s1 = self.tfa.generate_secret()
        s2 = self.tfa.generate_secret()
        assert s1 != s2

    def test_get_qr_url_format(self):
        url = self.tfa.get_qr_url("SECRET123", "user@test.com")
        assert "otpauth://totp/" in url
        assert "SECRET123" in url
        assert "user@test.com" in url
        assert "CAPTACAO_BLINDADA" in url

    def test_get_qr_url_custom_issuer(self):
        url = self.tfa.get_qr_url("S", "u", issuer="MyApp")
        assert "MyApp" in url

    def test_verify_code_wrong_length(self):
        assert self.tfa.verify_code("SECRET", "12345") is False

    def test_verify_code_non_numeric(self):
        assert self.tfa.verify_code("SECRET", "abcdef") is False

    def test_verify_code_empty(self):
        assert self.tfa.verify_code("SECRET", "") is False

    def test_verify_code_too_long(self):
        assert self.tfa.verify_code("SECRET", "1234567") is False

    def test_verify_code_with_valid_secret(self):
        """Generate a real TOTP code and verify it."""
        import hmac
        import struct
        import hashlib
        import base64

        secret = self.tfa.generate_secret()
        key = base64.b32decode(secret, casefold=True)
        counter = int(time.time()) // 30
        t = struct.pack(">Q", counter)
        h = hmac.HMAC(key, t, hashlib.sha1).digest()
        o = h[-1] & 0x0F
        otp = (struct.unpack(">I", h[o:o+4])[0] & 0x7FFFFFFF) % 1000000
        code = str(otp).zfill(6)

        assert self.tfa.verify_code(secret, code) is True


# =========================================================================
# SSOConfig
# =========================================================================

class TestSSOConfig:
    def setup_method(self):
        self.sso = SSOConfig()

    def test_not_enabled_by_default(self):
        assert self.sso.is_enabled("saml") is False

    def test_configure_provider(self):
        result = self.sso.configure("saml", enabled=True, client_id="cid")
        assert result is True

    def test_is_enabled_after_configure(self):
        self.sso.configure("saml", enabled=True)
        assert self.sso.is_enabled("saml") is True

    def test_is_enabled_disabled_provider(self):
        self.sso.configure("saml", enabled=False)
        assert self.sso.is_enabled("saml") is False

    def test_get_config_enabled(self):
        self.sso.configure("oauth", enabled=True)
        config = self.sso.get_config("oauth")
        assert config is not None
        assert config["provider"] == "oauth"
        assert config["enabled"] is True

    def test_get_config_disabled(self):
        self.sso.configure("saml", enabled=False)
        config = self.sso.get_config("saml")
        assert config is None

    def test_get_config_nonexistent(self):
        config = self.sso.get_config("nonexistent")
        assert config is None

    def test_multiple_providers(self):
        self.sso.configure("saml", enabled=True)
        self.sso.configure("oauth", enabled=True)
        assert self.sso.is_enabled("saml") is True
        assert self.sso.is_enabled("oauth") is True


# =========================================================================
# Global singletons
# =========================================================================

class TestGlobalSingletons:
    def test_get_api_key_manager_returns_instance(self):
        mgr = get_api_key_manager()
        assert isinstance(mgr, APIKeyManager)

    def test_get_api_key_manager_singleton(self):
        m1 = get_api_key_manager()
        m2 = get_api_key_manager()
        assert m1 is m2

    def test_get_2fa_returns_instance(self):
        tfa = get_2fa()
        assert isinstance(tfa, TwoFactorAuth)

    def test_get_sso_config_returns_instance(self):
        sso = get_sso_config()
        assert isinstance(sso, SSOConfig)
