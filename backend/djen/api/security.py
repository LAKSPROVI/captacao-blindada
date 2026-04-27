"""
Segurança Avançada para CAPTAÇÃO BLINDADA.

Inclui 2FA, API Keys e outras funcionalidades de segurança.
"""
import logging
import os
import secrets
import base64
import hashlib
import time
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

log = logging.getLogger("captacao.security")


# =============================================================================
# API Keys para Clientes
# =============================================================================

@dataclass
class APIKey:
    """Chave de API para cliente."""
    id: str
    key: str
    nome: str
    tenant_id: Optional[int]
    active: bool
    created_at: str
    expires_at: Optional[str]
    last_used: Optional[str]


class APIKeyManager:
    """Gerenciador de API Keys."""
    
    def __init__(self):
        self._keys: Dict[str, APIKey] = {}
        self._keys_by_value: Dict[str, APIKey] = {}
        self._lock = threading.Lock()
    
    def create_key(
        self,
        nome: str,
        tenant_id: Optional[int] = None,
        expires_days: Optional[int] = None,
    ) -> APIKey:
        """Cria novaAPI key."""
        key_id = secrets.token_hex(8)
        key_value = f"sk_{secrets.token_hex(32)}"
        
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        api_key = APIKey(
            id=key_id,
            key=key_value,
            nome=nome,
            tenant_id=tenant_id,
            active=True,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            last_used=None,
        )
        
        with self._lock:
            self._keys[key_id] = api_key
            self._keys_by_value[key_value] = api_key
        
        return api_key
    
    def validate_key(self, key: str) -> Optional[APIKey]:
        """Validauma API key."""
        with self._lock:
            api_key = self._keys_by_value.get(key)
            if not api_key:
                return None
            
            # Check se ativa
            if not api_key.active:
                return None
            
            # Check se expirou
            if api_key.expires_at:
                expires = datetime.fromisoformat(api_key.expires_at)
                if datetime.now() > expires:
                    return None
            
            # Update last used
            api_key.last_used = datetime.now().isoformat()
            
            return api_key
    
    def revoke_key(self, key_id: str) -> bool:
        """Revogauma API key."""
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].active = False
                return True
        return False
    
    def list_keys(self, tenant_id: Optional[int] = None) -> List[Dict]:
        """ListaKeys."""
        with self._lock:
            keys = list(self._keys.values())
            if tenant_id:
                keys = [k for k in keys if k.tenant_id == tenant_id]
            
            return [
                {
                    "id": k.id,
                    "nome": k.nome,
                    "active": k.active,
                    "created_at": k.created_at,
                    "expires_at": k.expires_at,
                    "last_used": k.last_used,
                }
                for k in keys
            ]


# =============================================================================
# 2FA/TOTP (Opcional)
# =============================================================================

class TwoFactorAuth:
    """
    Autenticaçãoem 2 fatores usando TOTP.
    
    É OPCIONAL - precisa ser habilitado pelo usuário.
    """
    
    @staticmethod
    def generate_secret() -> str:
        """Gera novo segredo."""
        return base64.b32encode(secrets.token_bytes(20)).decode()
    
    @staticmethod
    def get_qr_url(secret: str, account_name: str, issuer: str = "CAPTACAO_BLINDADA") -> str:
        """Retorna URL para QR code."""
        return f"otpauth://totp/{issuer}:{account_name}?secret={secret}&issuer={issuer}"
    
    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """Verifica código TOTP usando HMAC-based OTP."""
        if not (len(code) == 6 and code.isdigit()):
            return False
        try:
            import hmac
            import struct
            import time as _time
            key = base64.b32decode(secret, casefold=True)
            counter = int(_time.time()) // 30
            # Aceita janela de +/- 1 intervalo (90s total)
            for offset in (-1, 0, 1):
                t = struct.pack(">Q", counter + offset)
                h = hmac.HMAC(key, t, hashlib.sha1).digest()
                o = h[-1] & 0x0F
                otp = (struct.unpack(">I", h[o:o+4])[0] & 0x7FFFFFFF) % 1000000
                if int(code) == otp:
                    return True
            return False
        except Exception:
            return False


# =============================================================================
# SSO/SAML (Placeholder - Opcional)
# =============================================================================

class SSOConfig:
    """
    Configuração de SSO/SAML.
    
    É OPCIONAL - precisa ser configurado.
    """
    
    @dataclass
    class SSOProvider:
        provider: str  # "saml", "oauth", "azure", "google"
        enabled: bool
        client_id: Optional[str]
        client_secret: Optional[str]
        sso_url: Optional[str]
        idp_metadata: Optional[str]
    
    def __init__(self):
        self._providers: Dict[str, self.SSOProvider] = {}
    
    def configure(
        self,
        provider: str,
        enabled: bool = False,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> bool:
        """Configura provider SSO."""
        self._providers[provider] = self.SSOProvider(
            provider=provider,
            enabled=enabled,
            client_id=client_id,
            client_secret=client_secret,
            sso_url=None,
            idp_metadata=None,
        )
        return True
    
    def is_enabled(self, provider: str = "saml") -> bool:
        """Verifica seSSO está habilitado."""
        p = self._providers.get(provider)
        return p.enabled if p else False
    
    def get_config(self, provider: str = "saml") -> Optional[Dict]:
        """Retorna configuração."""
        p = self._providers.get(provider)
        if p and p.enabled:
            return {
                "provider": p.provider,
                "enabled": p.enabled,
                "sso_url": p.sso_url,
            }
        return None


# =============================================================================
# Instâncias Globais
# =============================================================================

_api_keys: Optional[APIKeyManager] = None
_2fa: Optional[TwoFactorAuth] = None
_sso: Optional[SSOConfig] = None
_lock = threading.Lock()


def get_api_key_manager() -> APIKeyManager:
    """Retorna gerenciador de API keys."""
    global _api_keys
    with _lock:
        if _api_keys is None:
            _api_keys = APIKeyManager()
    return _api_keys


def get_2fa() -> TwoFactorAuth:
    """Retorna gerenciador 2FA."""
    global _2fa
    with _lock:
        if _2fa is None:
            _2fa = TwoFactorAuth()
    return _2fa


def get_sso_config() -> SSOConfig:
    """Retorna configuração SSO."""
    global _sso
    with _lock:
        if _sso is None:
            _sso = SSOConfig()
    return _sso


log.debug("Security module loaded (2FA, API Keys, SSO - optional)")