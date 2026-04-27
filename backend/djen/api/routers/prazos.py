"""
Router de Prazos - CAPTAÇÃO BLINDADA.
Gerenciamento de prazos processuais.
"""
import logging
from datetime import date, timedelta, datetime
from typing import Optional, List

from fastapi import Request, APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.prazos")
router = APIRouter(prefix="/api/prazos", tags=["Prazos Processuais"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


FERIADOS_NACIONAIS = [
    (1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25),
]


def calcular_data_prazo(data_inicio: date, dias_uteis: int) -> date:
    """Calcula data final considerando dias úteis."""
    dias_contados = 0
    data_atual = data_inicio
    while dias_contados < dias_uteis:
        data_atual += timedelta(days=1)
        if data_atual.weekday() >= 5:
            continue
        if (data_atual.month, data_atual.day) in FERIADOS_NACIONAIS:
            continue
        dias_contados += 1
    return data_atual


class PrazoRequest(BaseModel):
    numero_processo: str
    descricao: str
    data_inicio: str
    dias_uteis: int
    tipo: str = "prazo"  # prazo, audiencia, pericia, diligencia


@router.post("/criar", summary="Criar prazo processual")
@limiter.limit("30/minute")
def criar_prazo(request: Request, req: PrazoRequest):
    """Cria um novo prazo processual com cálculo automático de dias úteis."""
    db = get_db()
    
    try:
        dt_inicio = date.fromisoformat(req.data_inicio)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use YYYY-MM-DD")
    
    dt_fim = calcular_data_prazo(dt_inicio, req.dias_uteis)
    
    cur = db.conn.execute(
        "INSERT INTO prazos (numero_processo, descricao, tipo, data_inicio, dias_uteis, data_fim) VALUES (?, ?, ?, ?, ?, ?)",
        (req.numero_processo, req.descricao, req.tipo, req.data_inicio, req.dias_uteis, dt_fim.isoformat())
    )
    db.conn.commit()
    
    return {
        "status": "success",
        "id": cur.lastrowid,
        "data_inicio": req.data_inicio,
        "dias_uteis": req.dias_uteis,
        "data_fim": dt_fim.isoformat(),
        "dia_semana": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][dt_fim.weekday()],
    }


@router.get("/listar", summary="Listar prazos")
@limiter.limit("60/minute")
def listar_prazos(request: Request, status: str = Query("ativo", description="ativo, vencido, todos"),
    limite: int = Query(100, ge=1, le=500),
):
    """Lista prazos processuais."""
    db = get_db()
    hoje = date.today().isoformat()
    
    if status == "ativo":
        rows = db.conn.execute(
            "SELECT * FROM prazos WHERE status = 'ativo' AND data_fim >= ? ORDER BY data_fim ASC LIMIT ?",
            (hoje, limite)
        ).fetchall()
    elif status == "vencido":
        rows = db.conn.execute(
            "SELECT * FROM prazos WHERE data_fim < ? OR status = 'vencido' ORDER BY data_fim DESC LIMIT ?",
            (hoje, limite)
        ).fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM prazos ORDER BY data_fim ASC LIMIT ?", (limite,)).fetchall()
    
    prazos = []
    for r in rows:
        d = dict(r)
        dt_fim = date.fromisoformat(d["data_fim"])
        dias_restantes = (dt_fim - date.today()).days
        d["dias_restantes"] = dias_restantes
        d["vencido"] = dias_restantes < 0
        d["urgente"] = 0 <= dias_restantes <= 3
        prazos.append(d)
    
    return {"status": "success", "total": len(prazos), "prazos": prazos}


@router.get("/proximos", summary="Próximos prazos a vencer")
@limiter.limit("60/minute")
def proximos_prazos(request: Request, dias: int = Query(7, ge=1, le=30)):
    """Lista prazos que vencem nos próximos X dias."""
    db = get_db()
    try:
        hoje = date.today().isoformat()
        limite = (date.today() + timedelta(days=dias)).isoformat()
        rows = db.conn.execute(
            "SELECT * FROM prazos WHERE status = 'ativo' AND data_fim >= ? AND data_fim <= ? ORDER BY data_fim ASC",
            (hoje, limite)
        ).fetchall()
        
        prazos = []
        for r in rows:
            d = dict(r)
            d["dias_restantes"] = (date.fromisoformat(d["data_fim"]) - date.today()).days
            prazos.append(d)
        
        return {"status": "success", "dias": dias, "total": len(prazos), "prazos": prazos}
    except Exception:
        return {"status": "success", "dias": dias, "total": 0, "prazos": []}


@router.delete("/{prazo_id}", summary="Remover prazo")
@limiter.limit("30/minute")
def remover_prazo(request: Request, prazo_id: int):
    """Remove um prazo."""
    db = get_db()
    db.conn.execute("DELETE FROM prazos WHERE id = ?", (prazo_id,))
    db.conn.commit()
    return {"status": "success", "message": "Prazo removido"}


@router.put("/{prazo_id}/concluir", summary="Marcar prazo como concluído")
@limiter.limit("30/minute")
def concluir_prazo(request: Request, prazo_id: int):
    """Marca prazo como concluído."""
    db = get_db()
    db.conn.execute("UPDATE prazos SET status = 'concluido' WHERE id = ?", (prazo_id,))
    db.conn.commit()
    return {"status": "success", "message": "Prazo concluído"}
