"""
Router de Kanban - CAPTAÇÃO BLINDADA.
Endpoints para gerenciamento visual de processos em formato Kanban.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from djen.api.database import Database

log = logging.getLogger("captacao.kanban")
router = APIRouter(prefix="/api/kanban", tags=["Kanban"])

def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()

def _ensure_tables(db):
    try:
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS kanban_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                numero_processo TEXT,
                coluna TEXT DEFAULT 'novo',
                prioridade TEXT DEFAULT 'normal',
                responsavel TEXT,
                cor TEXT DEFAULT '#3b82f6',
                ordem INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        db.conn.commit()
    except Exception:
        pass

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
def listar_colunas():
    return {"status": "success", "colunas": [
        {"id": "novo", "label": "Novo", "cor": "#3b82f6"},
        {"id": "em_analise", "label": "Em Análise", "cor": "#8b5cf6"},
        {"id": "aguardando", "label": "Aguardando", "cor": "#f59e0b"},
        {"id": "em_andamento", "label": "Em Andamento", "cor": "#10b981"},
        {"id": "concluido", "label": "Concluído", "cor": "#22c55e"},
        {"id": "arquivado", "label": "Arquivado", "cor": "#6b7280"},
    ]}

@router.get("/cards", summary="Listar cards do Kanban")
def listar_cards(coluna: Optional[str] = Query(None)):
    db = get_db()
    _ensure_tables(db)
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
def criar_card(req: KanbanCardRequest):
    db = get_db()
    _ensure_tables(db)
    cur = db.conn.execute(
        "INSERT INTO kanban_cards (titulo, descricao, numero_processo, coluna, prioridade, responsavel, cor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (req.titulo, req.descricao, req.numero_processo, req.coluna, req.prioridade, req.responsavel, req.cor)
    )
    db.conn.commit()
    return {"status": "success", "id": cur.lastrowid}

@router.put("/cards/{card_id}/mover", summary="Mover card entre colunas")
def mover_card(card_id: int, coluna: str = Body(...), ordem: int = Body(0)):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute("UPDATE kanban_cards SET coluna = ?, ordem = ?, atualizado_em = datetime('now','localtime') WHERE id = ?", (coluna, ordem, card_id))
    db.conn.commit()
    return {"status": "success", "id": card_id, "coluna": coluna}

@router.put("/cards/{card_id}", summary="Atualizar card")
def atualizar_card(card_id: int, req: KanbanCardRequest):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute(
        "UPDATE kanban_cards SET titulo=?, descricao=?, numero_processo=?, coluna=?, prioridade=?, responsavel=?, cor=?, atualizado_em=datetime('now','localtime') WHERE id=?",
        (req.titulo, req.descricao, req.numero_processo, req.coluna, req.prioridade, req.responsavel, req.cor, card_id)
    )
    db.conn.commit()
    return {"status": "success", "id": card_id}

@router.delete("/cards/{card_id}", summary="Remover card")
def remover_card(card_id: int):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute("DELETE FROM kanban_cards WHERE id = ?", (card_id,))
    db.conn.commit()
    return {"status": "success"}

@router.get("/stats", summary="Estatísticas do Kanban")
def kanban_stats():
    db = get_db()
    _ensure_tables(db)
    rows = db.conn.execute("SELECT coluna, COUNT(*) as c FROM kanban_cards GROUP BY coluna").fetchall()
    total = db.conn.execute("SELECT COUNT(*) as c FROM kanban_cards").fetchone()["c"]
    return {"status": "success", "total": total, "por_coluna": {r["coluna"]: r["c"] for r in rows}}
