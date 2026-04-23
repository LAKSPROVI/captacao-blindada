"""
Router de Agenda - CAPTAÇÃO BLINDADA.
Sistema de compromissos e audiências.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from djen.api.database import Database

log = logging.getLogger("captacao.agenda")
router = APIRouter(prefix="/api/agenda", tags=["Agenda"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


def _ensure_table(db):
    try:
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                tipo TEXT DEFAULT 'compromisso',
                numero_processo TEXT,
                data_evento TEXT NOT NULL,
                hora_evento TEXT,
                local TEXT,
                status TEXT DEFAULT 'pendente',
                lembrete_dias INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        db.conn.commit()
    except Exception:
        pass


class AgendaRequest(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    tipo: str = "compromisso"  # compromisso, audiencia, pericia, reuniao, prazo
    numero_processo: Optional[str] = None
    data_evento: str
    hora_evento: Optional[str] = None
    local: Optional[str] = None
    lembrete_dias: int = 1


@router.post("/criar", summary="Criar compromisso")
def criar_compromisso(req: AgendaRequest):
    db = get_db()
    _ensure_table(db)
    cur = db.conn.execute(
        """INSERT INTO agenda (titulo, descricao, tipo, numero_processo, data_evento, hora_evento, local, lembrete_dias)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (req.titulo, req.descricao, req.tipo, req.numero_processo, req.data_evento, req.hora_evento, req.local, req.lembrete_dias)
    )
    db.conn.commit()
    return {"status": "success", "id": cur.lastrowid}


@router.get("/listar", summary="Listar compromissos")
def listar_compromissos(
    status: str = Query("pendente", description="pendente, concluido, todos"),
    limite: int = Query(100, ge=1, le=500),
):
    db = get_db()
    _ensure_table(db)
    if status == "todos":
        rows = db.conn.execute("SELECT * FROM agenda ORDER BY data_evento ASC LIMIT ?", (limite,)).fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM agenda WHERE status = ? ORDER BY data_evento ASC LIMIT ?", (status, limite)).fetchall()
    
    compromissos = []
    for r in rows:
        d = dict(r)
        try:
            dt = date.fromisoformat(d["data_evento"])
            d["dias_restantes"] = (dt - date.today()).days
            d["passado"] = d["dias_restantes"] < 0
        except Exception:
            d["dias_restantes"] = None
            d["passado"] = False
        compromissos.append(d)
    
    return {"status": "success", "total": len(compromissos), "compromissos": compromissos}


@router.get("/proximos", summary="Próximos compromissos")
def proximos_compromissos(dias: int = Query(7, ge=1, le=60)):
    db = get_db()
    _ensure_table(db)
    hoje = date.today().isoformat()
    limite_data = (date.today() + timedelta(days=dias)).isoformat()
    rows = db.conn.execute(
        "SELECT * FROM agenda WHERE status = 'pendente' AND data_evento >= ? AND data_evento <= ? ORDER BY data_evento ASC",
        (hoje, limite_data)
    ).fetchall()
    
    compromissos = []
    for r in rows:
        d = dict(r)
        d["dias_restantes"] = (date.fromisoformat(d["data_evento"]) - date.today()).days
        compromissos.append(d)
    
    return {"status": "success", "dias": dias, "total": len(compromissos), "compromissos": compromissos}


@router.get("/hoje", summary="Compromissos de hoje")
def compromissos_hoje():
    db = get_db()
    _ensure_table(db)
    hoje = date.today().isoformat()
    rows = db.conn.execute(
        "SELECT * FROM agenda WHERE data_evento = ? ORDER BY hora_evento ASC", (hoje,)
    ).fetchall()
    return {"status": "success", "data": hoje, "total": len(rows), "compromissos": [dict(r) for r in rows]}


@router.put("/{compromisso_id}/concluir", summary="Concluir compromisso")
def concluir_compromisso(compromisso_id: int):
    db = get_db()
    _ensure_table(db)
    db.conn.execute("UPDATE agenda SET status = 'concluido' WHERE id = ?", (compromisso_id,))
    db.conn.commit()
    return {"status": "success"}


@router.delete("/{compromisso_id}", summary="Remover compromisso")
def remover_compromisso(compromisso_id: int):
    db = get_db()
    _ensure_table(db)
    db.conn.execute("DELETE FROM agenda WHERE id = ?", (compromisso_id,))
    db.conn.commit()
    return {"status": "success"}
