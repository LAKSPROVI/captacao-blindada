"""
Router de Configurações Avançadas - CAPTAÇÃO BLINDADA.

Endpoints para API Keys, 2FA, SSO, Cache, Backup, etc.
"""
import logging
import os
import re as _re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Body, Request
from pydantic import BaseModel, Field

from djen.api.ratelimit import limiter
from djen.api.auth import get_current_user, require_role, UserInDB
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
@limiter.limit("60/minute")
def listar_keys(
    request: Request,
    tenant_id: Optional[int] = None,
):
    """Lista todas as API keys."""
    manager = get_api_key_manager()
    keys = manager.list_keys(tenant_id)
    return {"status": "success", "keys": keys}


@router.post("/keys", summary="Criar API Key")
@limiter.limit("10/minute")
def criar_key(request: Request, body: CreateAPIKeyRequest = Body(...)):
    """Cria nova API key."""
    manager = get_api_key_manager()
    key = manager.create_key(
        nome=body.nome,
        tenant_id=body.tenant_id,
        expires_days=body.expires_days,
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
@limiter.limit("10/minute")
def revogar_key(request: Request, key_id: str):
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
    secret: str = Field(..., description="Segredo 2FA do usuario (gerado no setup)")


@router.post("/2fa/generate", summary="Gerar 2FA")
@limiter.limit("10/minute")
def gerar_2fa(request: Request, body: Enable2FARequest = Body(...)):
    """
    Gera segredo 2FA para usuário.
    
    Retorna URL para QR code.
    """
    tfa = get_2fa()
    secret = tfa.generate_secret()
    url = tfa.get_qr_url(secret, f"user_{body.user_id}")
    
    return {
        "status": "success",
        "secret": secret,
        "qr_url": url,
    }


@router.post("/2fa/verify", summary="Verificar código 2FA")
@limiter.limit("10/minute")
def verificar_2fa(request: Request, body: Verify2FARequest = Body(...)):
    """Verifica código 2FA."""
    tfa = get_2fa()
    valid = tfa.verify_code(body.secret, body.code)
    
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
@limiter.limit("60/minute")
def ver_sso(request: Request):
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
@limiter.limit("10/minute")
def configurar_sso(request: Request, body: ConfigureSSORequest = Body(...)):
    """Configura provider SSO."""
    sso = get_sso_config()
    sso.configure(
        provider=body.provider,
        enabled=body.enabled,
        client_id=body.client_id,
        client_secret=body.client_secret,
    )
    return {"status": "success", "message": f"SSO {body.provider} configurado"}


# =============================================================================
# Cache
# =============================================================================

@router.get("/cache/stats", summary="Estatísticas do cache")
@limiter.limit("60/minute")
def cache_stats(request: Request):
    """Retorna estatísticas do cache."""
    cache = get_cache()
    return {"status": "success", "stats": cache.stats()}


@router.post("/cache/clear", summary="Limpar cache")
@limiter.limit("10/minute")
def limpar_cache(request: Request):
    """Limpa todo cache."""
    cache = get_cache()
    cache.clear()
    return {"status": "success", "message": "Cache limpo"}


@router.post("/cache/redis", summary="Configurar Redis")
@limiter.limit("5/minute")
def configurar_redis(
    request: Request,
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
@limiter.limit("60/minute")
def listar_backups(request: Request):
    """Lista backups disponíveis."""
    manager = get_backup_manager()
    backups = manager.list_backups()
    return {"status": "success", "backups": backups}


@router.post("/backup", summary="Criar backup")
@limiter.limit("5/minute")
def criar_backup(request: Request):
    """Cria backup agora."""
    db_path = os.environ.get("CAPTACAO_DB_PATH", "/app/data/captacao_blindada.db")
    manager = get_backup_manager()
    path = manager.create_backup(db_path)
    if not path:
        raise HTTPException(status_code=500, detail="Erro ao criar backup")
    return {"status": "success", "path": path}


@router.post("/backup/{backup_name}/restore", summary="Restaurar backup")
@limiter.limit("5/minute")
def restaurar_backup(request: Request, backup_name: str):
    """Restaura backup."""
    # Validar nome do backup contra path traversal
    if not _re.match(r"^[\w\-\.]+$", backup_name):
        raise HTTPException(status_code=400, detail="Nome de backup invalido")
    db_path = os.environ.get("CAPTACAO_DB_PATH", "/app/data/captacao_blindada.db")
    manager = get_backup_manager()
    backup_path = f"{manager._backups_dir}/{backup_name}"
    success = manager.restore(backup_path, db_path)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao restaurar")
    return {"status": "success", "message": "Backup restaurado"}


@router.post("/backup/auto/start", summary="Iniciar backup automático")
@limiter.limit("5/minute")
def iniciar_backup_auto(request: Request, interval_hours: int = Body(24)):
    """Inicia backup automático."""
    db_path = os.environ.get("CAPTACAO_DB_PATH", "/app/data/captacao_blindada.db")
    manager = get_backup_manager()
    manager.configure()
    manager.auto_backup(db_path, interval_hours)
    return {"status": "success", "message": f"Backup automático a cada {interval_hours}h"}


@router.post("/backup/auto/stop", summary="Parar backup automático")
@limiter.limit("5/minute")
def parar_backup_auto(request: Request):
    """Para backup automático."""
    manager = get_backup_manager()
    manager.stop()
    return {"status": "success", "message": "Backup automático parado"}


# =============================================================================
# Configurações Globais
# =============================================================================

@router.get("/settings", summary="Listar configurações globais")
@limiter.limit("60/minute")
def listar_settings(request: Request):
    """Lista todas as configurações globais do sistema."""
    from djen.api.database import get_database
    db = get_database()
    try:
        rows = db.conn.execute("SELECT * FROM system_settings").fetchall()
        return {"status": "success", "settings": {r["key"]: r["value"] for r in rows}}
    except Exception:
        return {"status": "success", "settings": {}}


@router.put("/settings/{key}", summary="Atualizar configuração")
@limiter.limit("30/minute")
def atualizar_setting(request: Request, key: str, value: str = Body(...)):
    """Atualiza uma configuração global."""
    from djen.api.database import get_database
    db = get_database()
    try:
        db.conn.execute("INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, datetime('now','localtime'))", (key, value))
        db.conn.commit()
        return {"status": "success", "key": key, "value": value}
    except Exception as e:
        log.error("Erro ao atualizar setting %s: %s", key, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao acessar banco de dados")


# =============================================================================
# Limpeza de Dados Antigos (Purge)
# =============================================================================

@router.post("/purge/execucoes", summary="Limpar execuções antigas")
@limiter.limit("5/minute")
def purge_execucoes(request: Request, dias: int = Body(90, description="Manter últimos X dias")):
    """Remove execuções mais antigas que X dias."""
    from djen.api.database import get_database
    db = get_database()
    cur = db.conn.execute(
        "DELETE FROM execucoes_captacao WHERE date(inicio) < date('now','localtime', ? || ' days')",
        (f"-{dias}",)
    )
    db.conn.commit()
    return {"status": "success", "removidos": cur.rowcount, "dias_mantidos": dias}


@router.post("/purge/erros", summary="Limpar erros resolvidos antigos")
@limiter.limit("5/minute")
def purge_erros(request: Request, dias: int = Body(30, description="Manter últimos X dias")):
    """Remove erros resolvidos mais antigos que X dias."""
    from djen.api.database import get_database
    db = get_database()
    cur = db.conn.execute(
        "DELETE FROM system_errors WHERE status='resolvido' AND date(criado_em) < date('now','localtime', ? || ' days')",
        (f"-{dias}",)
    )
    db.conn.commit()
    return {"status": "success", "removidos": cur.rowcount, "dias_mantidos": dias}


@router.post("/purge/audit", summary="Limpar logs de auditoria antigos")
@limiter.limit("5/minute")
def purge_audit(request: Request, dias: int = Body(180, description="Manter últimos X dias")):
    """Remove logs de auditoria mais antigos que X dias."""
    from djen.api.database import get_database
    db = get_database()
    cur = db.conn.execute(
        "DELETE FROM audit_logs WHERE date(criado_em) < date('now','localtime', ? || ' days')",
        (f"-{dias}",)
    )
    db.conn.commit()
    return {"status": "success", "removidos": cur.rowcount, "dias_mantidos": dias}


# =============================================================================
# Importar/Exportar Captações
# =============================================================================

@router.get("/captacoes/exportar", summary="Exportar todas as captações em JSON")
@limiter.limit("5/minute")
def exportar_captacoes(request: Request):
    """Exporta todas as captações configuradas em JSON."""
    import json as _json
    from fastapi.responses import StreamingResponse
    from djen.api.database import get_database
    db = get_database()
    rows = db.conn.execute("SELECT * FROM captacoes ORDER BY id").fetchall()
    data = _json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2, default=str)
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=captacoes_export.json"}
    )


@router.post("/captacoes/importar", summary="Importar captações de JSON")
@limiter.limit("5/minute")
def importar_captacoes(request: Request, captacoes: list = Body(...)):
    """Importa captações a partir de lista JSON."""
    from djen.api.database import get_database
    db = get_database()
    importados = 0
    erros = []
    for cap in captacoes:
        try:
            db.criar_captacao(
                nome=cap.get("nome", "Importada"),
                tipo_busca=cap.get("tipo_busca", "processo"),
                **{k: v for k, v in cap.items() if k not in ("id", "nome", "tipo_busca", "criado_em", "atualizado_em")}
            )
            importados += 1
        except Exception as e:
            erros.append({"nome": cap.get("nome"), "erro": str(e)})
    return {"status": "success", "importados": importados, "erros": erros}


# =============================================================================
# Alerta Saldo Baixo
# =============================================================================

@router.get("/billing/alerta-saldo", summary="Verificar saldo baixo")
@limiter.limit("60/minute")
def alerta_saldo(request: Request, threshold: int = 1000):
    """Verifica se o saldo está abaixo do threshold."""
    from djen.api.database import get_database
    db = get_database()
    try:
        tenant = db.conn.execute("SELECT * FROM tenants LIMIT 1").fetchone()
        if not tenant:
            return {"status": "ok", "message": "Nenhum tenant encontrado"}
        saldo = dict(tenant).get("saldo_tokens", 0)
        baixo = saldo < threshold
        return {
            "status": "warning" if baixo else "ok",
            "saldo_atual": saldo,
            "threshold": threshold,
            "alerta": baixo,
            "message": f"Saldo baixo! Apenas {saldo} tokens restantes." if baixo else "Saldo OK",
        }
    except Exception as e:
        log.error("Erro ao verificar saldo: %s", e, exc_info=True)
        return {"status": "error", "message": "Erro ao acessar banco de dados"}


# =============================================================================
# Upload CSV de Processos
# =============================================================================

@router.post("/processos/upload-csv", summary="Importar processos via CSV")
@limiter.limit("5/minute")
def upload_csv_processos(request: Request, processos: list = Body(..., description="Lista de {numero_processo, tribunal}")):
    """Importa múltiplos processos para monitoramento."""
    from djen.api.database import get_database
    db = get_database()
    importados = 0
    erros = []
    for p in processos:
        try:
            num = p.get("numero_processo", "").strip()
            if not num:
                continue
            db.registrar_processo_monitorado(
                numero_processo=num,
                tribunal=p.get("tribunal"),
                origem="csv_import",
            )
            importados += 1
        except Exception as e:
            erros.append({"numero_processo": p.get("numero_processo"), "erro": str(e)})
    return {"status": "success", "importados": importados, "erros": erros}