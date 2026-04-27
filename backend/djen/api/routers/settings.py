"""
Router de Configuracoes do Sistema.
Permite configurar intervalos de scheduler e outros parametros globais.
"""

import logging
from typing import Dict, Any
from fastapi import Request, APIRouter, Depends, HTTPException, Body
from djen.api.database import Database
from djen.api.auth import get_current_user, require_role, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.settings")
router = APIRouter(prefix="/api/settings", tags=["Configuracoes"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("", summary="Listar todas as configuracoes")
@limiter.limit("60/minute")
def listar_settings(request: Request, current_user: UserInDB = Depends(require_role("master"))):
    db = get_db()
    return db.listar_settings()


@router.post("", summary="Atualizar uma configuracao")
@limiter.limit("30/minute")
def atualizar_setting(request: Request, payload: Dict[str, Any] = Body(...), current_user: UserInDB = Depends(require_role("master"))):
    """
    Atualiza uma configuracao global.
    Ex: {"key": "datajud_update_interval_hours", "value": "12"}
    """
    key = payload.get("key")
    value = payload.get("value")
    
    if not key or value is None:
        raise HTTPException(status_code=400, detail="Key and value are required")
        
    db = get_db()
    db.set_setting(key, value)
    
    # Se for a configuracao de intervalo do DataJud, reagendar o job
    if key == "datajud_update_interval_hours":
        try:
            from djen.api.app import reschedule_datajud_job
            reschedule_datajud_job(int(value))
        except Exception as e:
            log.error("Erro ao reagendar job: %s", e)
            
    return {"status": "success", "message": f"Setting '{key}' atualizada"}
