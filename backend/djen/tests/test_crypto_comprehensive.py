"""
Comprehensive tests for djen.api.crypto module.

Tests Fernet encryption/decryption with edge cases.
"""

import os
import pytest

# Set encryption key before importing
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-for-testing-32!")

# Reset the cached fernet instance so our key takes effect
import djen.api.crypto as crypto_mod
crypto_mod._fernet = None

from djen.api.crypto import encrypt_value, decrypt_value


# =========================================================================
# Encryption
# =========================================================================

class TestEncryption:
    def test_encrypt_returns_string(self):
        result = encrypt_value("hello")
        assert isinstance(result, str)
        assert result != "hello"

    def test_encrypt_empty_returns_empty(self):
        assert encrypt_value("") == ""

    def test_encrypt_different_each_time(self):
        """Fernet uses random IV, so same plaintext produces different ciphertext."""
        c1 = encrypt_value("same")
        c2 = encrypt_value("same")
        assert c1 != c2

    def test_encrypt_unicode(self):
        result = encrypt_value("açãoéàü日本語")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encrypt_long_string(self):
        long_str = "A" * 10000
        result = encrypt_value(long_str)
        assert isinstance(result, str)

    def test_encrypt_special_chars(self):
        result = encrypt_value("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        assert isinstance(result, str)

    def test_encrypt_newlines(self):
        result = encrypt_value("line1\nline2\nline3")
        assert isinstance(result, str)

    def test_encrypt_json_string(self):
        result = encrypt_value('{"key": "value", "num": 42}')
        assert isinstance(result, str)


# =========================================================================
# Decryption
# =========================================================================

class TestDecryption:
    def test_decrypt_empty_returns_empty(self):
        assert decrypt_value("") == ""

    def test_decrypt_roundtrip(self):
        original = "secret data"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_decrypt_unicode_roundtrip(self):
        original = "açãoéàü日本語"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_decrypt_long_string_roundtrip(self):
        original = "B" * 10000
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_decrypt_invalid_ciphertext_returns_empty(self):
        result = decrypt_value("not-valid-ciphertext")
        assert result == ""

    def test_decrypt_random_base64_returns_empty(self):
        import base64
        fake = base64.urlsafe_b64encode(b"random data").decode()
        result = decrypt_value(fake)
        assert result == ""

    def test_decrypt_special_chars_roundtrip(self):
        original = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt_value(original)
        assert decrypt_value(encrypted) == original

    def test_decrypt_json_roundtrip(self):
        original = '{"api_key": "sk-12345", "secret": "abc"}'
        encrypted = encrypt_value(original)
        assert decrypt_value(encrypted) == original

    def test_multiple_roundtrips(self):
        for i in range(20):
            original = f"test_value_{i}_{'x' * i}"
            encrypted = encrypt_value(original)
            assert decrypt_value(encrypted) == original


# =========================================================================
# Key handling
# =========================================================================

class TestKeyHandling:
    def test_missing_key_raises_error(self):
        """Without ENCRYPTION_KEY, _get_fernet should raise."""
        old_key = os.environ.get("ENCRYPTION_KEY")
        old_fernet = crypto_mod._fernet
        try:
            os.environ.pop("ENCRYPTION_KEY", None)
            crypto_mod._fernet = None
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
                encrypt_value("test")
        finally:
            if old_key:
                os.environ["ENCRYPTION_KEY"] = old_key
            crypto_mod._fernet = old_fernet
