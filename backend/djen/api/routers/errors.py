import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from djen.api.auth import get_current_user, require_role, UserInDB
from djen.api.database import get_database

log = logging.getLogger("captacao.routers.errors")

router = APIRouter(prefix="/api/errors", tags=["Erros"])

class SystemErrorResponse(BaseModel):
    id: int
    tenant_id: int | None
    user_id: int | None
    function_name: str
    error_type: str
    error_message: str
    stack_trace: str | None
    status: str
    resolvido_em: str | None
    criado_em: str

@router.get("/", response_model=List[SystemErrorResponse])
def listar_erros(limit: int = 100, offset: int = 0, status: str = "aberto", current_user: UserInDB = Depends(require_role("master"))):
    """(Master) Lista erros do sistema, agrupados por abertos ou fechados."""
    db = get_database()
    query = "SELECT * FROM system_errors"
    params = []
    
    if status and status != "all":
        query += " WHERE status = ?"
        params.append(status)
        
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.conn.execute(query, params).fetchall()
    return [SystemErrorResponse(**dict(r)) for r in rows]


@router.get("/recent", response_model=List[SystemErrorResponse])
def listar_erros_recentes(limit: int = 20, current_user: UserInDB = Depends(require_role("master"))):
    """(Master) Lista erros recentes do sistema."""
    db = get_database()
    rows = db.conn.execute(
        "SELECT * FROM system_errors ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [SystemErrorResponse(**dict(r)) for r in rows]

@router.post("/{error_id}/resolve")
def resolver_erro(error_id: int, current_user: UserInDB = Depends(require_role("master"))):
    """(Master) Marca o erro do sistema como resolvido."""
    db = get_database()
    # Verifica
    row = db.conn.execute("SELECT * FROM system_errors WHERE id = ?", (error_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Erro nao encontrado.")
    
    db.conn.execute("UPDATE system_errors SET status = 'resolvido', resolvido_em = datetime('now') WHERE id = ?", (error_id,))
    db.conn.commit()
    
    return {"status": "success", "message": "Erro marcado como resolvido."}
