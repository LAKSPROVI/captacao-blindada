"""
Router de Configurações Avançadas - CAPTAÇÃO BLINDADA.

Endpoints para API Keys, 2FA, SSO, Cache, Backup, etc.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from djen.api.security import (
    get_api_key_manager,
    get_2fa,
    get_sso_config,
    APIKeyManager,
    TwoFactorAuth,
)
from djen.api.cache import get_cache, CacheManager
from djen.api.backup import get_backup_manager, BackupManager

log = logging.getLogger("captacao.advanced")
router = APIRouter(prefix="/api/config", tags=["Configuracoes Avancadas"])


# =============================================================================
# API Keys
# =============================================================================

class CreateAPIKeyRequest(BaseModel):
    """Request para criar API key."""
    nome: str = Field(..., description="Nome da key")
    tenant_id: Optional[int] = Field(None, description="ID do tenant")
    expires_days: Optional[int] = Field(None, description="Dias até expirar")


@router.get("/keys", summary="Listar API Keys")
def listar_keys(
    tenant_id: Optional[int] = None,
):
    """Lista todas as API keys."""
    manager = get_api_key_manager()
    keys = manager.list_keys(tenant_id)
    return {"status": "success", "keys": keys}


@router.post("/keys", summary="Criar API Key")
def criar_key(request: CreateAPIKeyRequest):
    """Cria nova API key."""
    manager = get_api_key_manager()
    key = manager.create_key(
        nome=request.nome,
        tenant_id=request.tenant_id,
        expires_days=request.expires_days,
    )
    return {
        "status": "success",
        "key": {
            "id": key.id,
            "key": key.key,  # Only returned once!
            "nome": key.nome,
            "expires_at": key.expires_at,
        }
    }


@router.delete("/keys/{key_id}", summary="Revogar API Key")
def revogar_key(key_id: str):
    """Revoga uma API key."""
    manager = get_api_key_manager()
    success = manager.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key não encontrada")
    return {"status": "success", "message": "Key revogada"}


# =============================================================================
# 2FA (Opcional)
# =============================================================================

class Enable2FARequest(BaseModel):
    """Request para habilitar 2FA."""
    user_id: int


class Verify2FARequest(BaseModel):
    """Request para verificar 2FA."""
    user_id: int
    code: str


@router.post("/2fa/generate", summary="Gerar 2FA")
def gerar_2fa(request: Enable2FARequest):
    """
    Gera segredo 2FA para usuário.
    
    Retorna URL para QR code.
    """
    tfa = get_2fa()
    secret = tfa.generate_secret()
    url = tfa.get_qr_url(secret, f"user_{request.user_id}")
    
    return {
        "status": "success",
        "secret": secret,
        "qr_url": url,
    }


@router.post("/2fa/verify", summary="Verificar código 2FA")
def verificar_2fa(request: Verify2FARequest):
    """Verifica código 2FA."""
    tfa = get_2fa()
    # Em produção, buscar secret do usuário
    valid = tfa.verify_code("test_secret", request.code)
    
    return {
        "status": "success",
        "valid": valid,
    }


# =============================================================================
# SSO (Opcional)
# =============================================================================

class ConfigureSSORequest(BaseModel):
    """Request para configurar SSO."""
    provider: str = Field(..., description="Provider: saml, oauth, azure, google")
    enabled: bool = Field(False, description="Habilitar")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


@router.get("/sso", summary="Verificar SSO")
def ver_sso():
    """Verifica configuração SSO."""
    sso = get_sso_config()
    return {
        "status": "success",
        "providers": {
            "saml": sso.get_config("saml"),
            "oauth": sso.get_config("oauth"),
            "azure": sso.get_config("azure"),
        }
    }


@router.post("/sso", summary="Configurar SSO")
def configurar_sso(request: ConfigureSSORequest):
    """Configura provider SSO."""
    sso = get_sso_config()
    sso.configure(
        provider=request.provider,
        enabled=request.enabled,
        client_id=request.client_id,
        client_secret=request.client_secret,
    )
    return {"status": "success", "message": f"SSO {request.provider} configurado"}


# =============================================================================
# Cache
# =============================================================================

@router.get("/cache/stats", summary="Estatísticas do cache")
def cache_stats():
    """Retorna estatísticas do cache."""
    cache = get_cache()
    return {"status": "success", "stats": cache.stats()}


@router.post("/cache/clear", summary="Limpar cache")
def limpar_cache():
    """Limpa todo cache."""
    cache = get_cache()
    cache.clear()
    return {"status": "success", "message": "Cache limpo"}


@router.post("/cache/redis", summary="Configurar Redis")
def configurar_redis(
    host: str = Body("localhost"),
    port: int = Body(6379),
    password: Optional[str] = Body(None),
):
    """Configura Redis (opcional)."""
    cache = get_cache()
    success = cache.configure_redis(host=host, port=port, password=password)
    return {
        "status": "success",
        "connected": success,
        "backend": "redis" if success else "memory",
    }


# =============================================================================
# Backup
# =============================================================================

@router.get("/backup", summary="Listar backups")
def listar_backups():
    """Lista backups disponíveis."""
    manager = get_backup_manager()
    backups = manager.list_backups()
    return {"status": "success", "backups": backups}


@router.post("/backup", summary="Criar backup")
def criar_backup(
    db_path: str = Body("/app/data/captacao_blindada.db"),
):
    """Cria backup agora."""
    manager = get_backup_manager()
    path = manager.create_backup(db_path)
    if not path:
        raise HTTPException(status_code=500, detail="Erro ao criar backup")
    return {"status": "success", "path": path}


@router.post("/backup/{backup_name}/restore", summary="Restaurar backup")
def restaurar_backup(
    backup_name: str,
    db_path: str = Body("/app/data/captacao_blindada.db"),
):
    """Restaura backup."""
    manager = get_backup_manager()
    backup_path = f"{manager._backups_dir}/{backup_name}"
    success = manager.restore(backup_path, db_path)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao restaurar")
    return {"status": "success", "message": "Backup restaurado"}


@router.post("/backup/auto/start", summary="Iniciar backup automático")
def iniciar_backup_auto(
    interval_hours: int = Body(24),
    db_path: str = Body("/app/data/captacao_blindada.db"),
):
    """Inicia backup automático."""
    manager = get_backup_manager()
    manager.configure()
    manager.auto_backup(db_path, interval_hours)
    return {"status": "success", "message": f"Backup automático a cada {interval_hours}h"}


@router.post("/backup/auto/stop", summary="Parar backup automático")
def parar_backup_auto():
    """Para backup automático."""
    manager = get_backup_manager()
    manager.stop()
    return {"status": "success", "message": "Backup automático parado"}