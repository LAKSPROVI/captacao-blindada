import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
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


@router.post("/notify-critical", summary="Notificar erro crítico por email")
def notify_critical(error_id: int = Body(...), current_user: UserInDB = Depends(require_role("master"))):
    """Envia notificação por email sobre erro crítico."""
    db = get_database()
    error = db.conn.execute("SELECT * FROM system_errors WHERE id = ?", (error_id,)).fetchone()
    if not error:
        raise HTTPException(status_code=404, detail="Erro não encontrado")
    e = dict(error)
    try:
        from djen.api.notifications import get_notification_manager
        import os
        manager = get_notification_manager()
        email_to = os.environ.get("NOTIFICATION_EMAIL", "")
        if manager.email.enabled and email_to:
            subject = f"[CRITICO] {e.get('error_type', 'Erro')} em {e.get('function_name', 'N/A')}"
            body = f"ERRO CRITICO\n\nTipo: {e.get('error_type')}\nFuncao: {e.get('function_name')}\nMsg: {e.get('error_message')}\nData: {e.get('criado_em')}\n\nStack:\n{(e.get('stack_trace') or '')[:1000]}"
            success = manager.email.send(email_to, subject, body)
            return {"status": "success" if success else "error", "message": "Email enviado" if success else "Falha"}
        return {"status": "warning", "message": "Email nao configurado. Configure SMTP_HOST e NOTIFICATION_EMAIL no .env"}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}


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
