import logging
import json
import csv
import io
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
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
def listar_auditoria(
    limit: int = 500,
    offset: int = 0,
    action: str = Query(None, description="Filtrar por ação"),
    entity_type: str = Query(None, description="Filtrar por tipo de entidade"),
    current_user: UserInDB = Depends(require_role("master"))
):
    """(Master) Lista a cadeia de custodia (logs)."""
    db = get_database()
    conditions = []
    params: list = []
    
    if action:
        conditions.append("action = ?")
        params.append(action)
    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)
    
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM audit_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.conn.execute(sql, params).fetchall()
    return [AuditLogResponse(**dict(r)) for r in rows]


@router.get("/stats")
def audit_stats(current_user: UserInDB = Depends(require_role("master"))):
    """(Master) Estatísticas da cadeia de custódia."""
    db = get_database()
    
    total = db.conn.execute("SELECT COUNT(*) as c FROM audit_logs").fetchone()["c"]
    hoje = db.conn.execute(
        "SELECT COUNT(*) as c FROM audit_logs WHERE date(criado_em) = date('now', 'localtime')"
    ).fetchone()["c"]
    
    por_acao = db.conn.execute(
        "SELECT action, COUNT(*) as c FROM audit_logs GROUP BY action ORDER BY c DESC LIMIT 20"
    ).fetchall()
    
    por_entidade = db.conn.execute(
        "SELECT entity_type, COUNT(*) as c FROM audit_logs GROUP BY entity_type ORDER BY c DESC LIMIT 20"
    ).fetchall()
    
    por_usuario = db.conn.execute(
        "SELECT user_id, COUNT(*) as c FROM audit_logs WHERE user_id IS NOT NULL GROUP BY user_id ORDER BY c DESC LIMIT 10"
    ).fetchall()
    
    return {
        "total": total,
        "hoje": hoje,
        "por_acao": {r["action"]: r["c"] for r in por_acao},
        "por_entidade": {r["entity_type"]: r["c"] for r in por_entidade},
        "por_usuario": {str(r["user_id"]): r["c"] for r in por_usuario},
    }


@router.get("/export/csv")
def exportar_csv(
    limit: int = 10000,
    action: str = Query(None),
    entity_type: str = Query(None),
    current_user: UserInDB = Depends(require_role("master"))
):
    """(Master) Exporta cadeia de custódia em CSV."""
    db = get_database()
    conditions = []
    params: list = []
    
    if action:
        conditions.append("action = ?")
        params.append(action)
    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)
    
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM audit_logs {where} ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    rows = db.conn.execute(sql, params).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Data/Hora", "Ação", "Entidade", "Alvo", "Tenant", "Usuário", "IP", "Detalhes", "Hash SHA-256"])
    
    for r in rows:
        d = dict(r)
        writer.writerow([
            d["id"],
            d["criado_em"],
            d["action"],
            d["entity_type"],
            d["entity_id"] or "",
            d["tenant_id"] or "SYS",
            d["user_id"] or "ROOT",
            d["ip_address"] or "",
            d["details"] or "",
            d["data_hash"],
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cadeia_custodia.csv"}
    )


@router.get("/export/json")
def exportar_json(
    limit: int = 10000,
    action: str = Query(None),
    entity_type: str = Query(None),
    current_user: UserInDB = Depends(require_role("master"))
):
    """(Master) Exporta cadeia de custódia em JSON."""
    db = get_database()
    conditions = []
    params: list = []
    
    if action:
        conditions.append("action = ?")
        params.append(action)
    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)
    
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM audit_logs {where} ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    rows = db.conn.execute(sql, params).fetchall()
    data = [dict(r) for r in rows]
    
    output = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([output]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=cadeia_custodia.json"}
    )


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
            previous_hash = d["data_hash"]
        else:
            previous_hash = expected_hash
            
    if erros:
        return {"status": "error", "message": "FALHA DE INTEGRIDADE ENCONTRADA MODO ROOT", "erros": erros}
        
    return {"status": "ok", "message": "A cadeia de custodia esta integra. 0 (zero) modificacoes diretas em banco identificadas.", "total_verificados": len(rows)}
