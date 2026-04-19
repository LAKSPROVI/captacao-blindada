"""
Router de Configuracoes do Sistema.
Permite configurar intervalos de scheduler e outros parametros globais.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Body
from djen.api.database import Database

log = logging.getLogger("captacao.settings")
router = APIRouter(prefix="/api/settings", tags=["Configuracoes"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("", summary="Listar todas as configuracoes")
def listar_settings():
    db = get_db()
    return db.listar_settings()


@router.post("", summary="Atualizar uma configuracao")
def atualizar_setting(payload: Dict[str, Any] = Body(...)):
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
