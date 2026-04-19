import logging
import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from djen.api.auth import get_current_user, require_role, UserInDB
from djen.api.database import get_database
from djen.api.audit import _hash_data

log = logging.getLogger("captacao.routers.audit")

router = APIRouter(prefix="/api/audit", tags=["Auditoria"])

class AuditLogResponse(BaseModel):
    id: int
    tenant_id: int | None
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    details: str | None
    ip_address: str | None
    data_hash: str
    criado_em: str

@router.get("/logs", response_model=List[AuditLogResponse])
def listar_auditoria(limit: int = 100, offset: int = 0, current_user: UserInDB = Depends(require_role("master"))):
    """(Master) Lista a cadeia de custodia (logs)."""
    db = get_database()
    rows = db.conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return [AuditLogResponse(**dict(r)) for r in rows]

@router.get("/verify")
def verificar_cadeia(current_user: UserInDB = Depends(require_role("master"))):
    """Valida a cadeia de hashes do banco para garantir integridade e que logs nao foram apagados ou editados manualmente."""
    db = get_database()
    rows = db.conn.execute("SELECT * FROM audit_logs ORDER BY id ASC").fetchall()
    
    previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    
    erros = []
    
    for row in rows:
        d = dict(row)
        action = d["action"]
        entity_type = d["entity_type"]
        entity_id = d["entity_id"]
        tenant_id = d["tenant_id"]
        user_id = d["user_id"]
        details_str = d["details"] or ""
        
        payload_str = f"{action}:{entity_type}:{entity_id}:{tenant_id}:{user_id}:{details_str}"
        
        expected_hash = _hash_data(previous_hash, payload_str)
        if expected_hash != d["data_hash"]:
            erros.append({
                "id": d["id"],
                "expected_hash": expected_hash,
                "found_hash": d["data_hash"]
            })
            # A cadeia quebra daqui em diante
            previous_hash = d["data_hash"] # continurar checando apartir do db
        else:
            previous_hash = expected_hash
            
    if erros:
        return {"status": "error", "message": "FALHA DE INTEGRIDADE ENCONTRADA MODO ROOT", "erros": erros}
        
    return {"status": "ok", "message": "A cadeia de custodia esta integra. 0 (zero) modificacoes diretas em banco identificadas."}
