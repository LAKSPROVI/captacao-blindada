"""
Router de Kanban - CAPTAÇÃO BLINDADA.
Endpoints para gerenciamento visual de processos em formato Kanban.
"""
import logging
from typing import Optional
from fastapi import Request, APIRouter, Depends, Query, Body
from pydantic import BaseModel
from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.kanban")
router = APIRouter(prefix="/api/kanban", tags=["Kanban"])

def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()

class KanbanCardRequest(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    numero_processo: Optional[str] = None
    coluna: str = "novo"
    prioridade: str = "normal"
    responsavel: Optional[str] = None
    cor: Optional[str] = "#3b82f6"

COLUNAS = ["novo", "em_analise", "aguardando", "em_andamento", "concluido", "arquivado"]

@router.get("/colunas", summary="Listar colunas do Kanban")
@limiter.limit("60/minute")
def listar_colunas(request: Request, current_user: UserInDB = Depends(get_current_user)):
    return {"status": "success", "colunas": [
        {"id": "novo", "label": "Novo", "cor": "#3b82f6"},
        {"id": "em_analise", "label": "Em Análise", "cor": "#8b5cf6"},
        {"id": "aguardando", "label": "Aguardando", "cor": "#f59e0b"},
        {"id": "em_andamento", "label": "Em Andamento", "cor": "#10b981"},
        {"id": "concluido", "label": "Concluído", "cor": "#22c55e"},
        {"id": "arquivado", "label": "Arquivado", "cor": "#6b7280"},
    ]}

@router.get("/cards", summary="Listar cards do Kanban")
@limiter.limit("60/minute")
def listar_cards(request: Request, coluna: Optional[str] = Query(None), current_user: UserInDB = Depends(get_current_user)):
    db = get_db()

    if coluna:
        rows = db.conn.execute("SELECT * FROM kanban_cards WHERE coluna = ? ORDER BY ordem ASC", (coluna,)).fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM kanban_cards ORDER BY coluna, ordem ASC").fetchall()
    
    cards_by_col = {}
    for r in rows:
        d = dict(r)
        col = d["coluna"]
        if col not in cards_by_col:
            cards_by_col[col] = []
        cards_by_col[col].append(d)
    
    return {"status": "success", "total": len(rows), "cards": cards_by_col}

@router.post("/cards", summary="Criar card")
@limiter.limit("30/minute")
def criar_card(request: Request, req: KanbanCardRequest, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()

    cur = db.conn.execute(
        "INSERT INTO kanban_cards (titulo, descricao, numero_processo, coluna, prioridade, responsavel, cor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (req.titulo, req.descricao, req.numero_processo, req.coluna, req.prioridade, req.responsavel, req.cor)
    )
    db.conn.commit()
    return {"status": "success", "id": cur.lastrowid}

@router.put("/cards/{card_id}/mover", summary="Mover card entre colunas")
@limiter.limit("30/minute")
def mover_card(request: Request, card_id: int, coluna: str = Body(...), ordem: int = Body(0), current_user: UserInDB = Depends(get_current_user)):
    db = get_db()

    db.conn.execute("UPDATE kanban_cards SET coluna = ?, ordem = ?, atualizado_em = datetime('now','localtime') WHERE id = ?", (coluna, ordem, card_id))
    db.conn.commit()
    return {"status": "success", "id": card_id, "coluna": coluna}

@router.put("/cards/{card_id}", summary="Atualizar card")
@limiter.limit("30/minute")
def atualizar_card(request: Request, card_id: int, req: KanbanCardRequest, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()

    db.conn.execute(
        "UPDATE kanban_cards SET titulo=?, descricao=?, numero_processo=?, coluna=?, prioridade=?, responsavel=?, cor=?, atualizado_em=datetime('now','localtime') WHERE id=?",
        (req.titulo, req.descricao, req.numero_processo, req.coluna, req.prioridade, req.responsavel, req.cor, card_id)
    )
    db.conn.commit()
    return {"status": "success", "id": card_id}

@router.delete("/cards/{card_id}", summary="Remover card")
@limiter.limit("30/minute")
def remover_card(request: Request, card_id: int, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()

    db.conn.execute("DELETE FROM kanban_cards WHERE id = ?", (card_id,))
    db.conn.commit()
    return {"status": "success"}

@router.get("/stats", summary="Estatísticas do Kanban")
@limiter.limit("60/minute")
def kanban_stats(request: Request, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()

    rows = db.conn.execute("SELECT coluna, COUNT(*) as c FROM kanban_cards GROUP BY coluna").fetchall()
    total = db.conn.execute("SELECT COUNT(*) as c FROM kanban_cards").fetchone()["c"]
    return {"status": "success", "total": total, "por_coluna": {r["coluna"]: r["c"] for r in rows}}
