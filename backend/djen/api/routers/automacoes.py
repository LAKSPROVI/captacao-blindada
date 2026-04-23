"""
Router de Automações - CAPTAÇÃO BLINDADA.
Endpoints para automações e regras do sistema.
"""
import logging
import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

from djen.api.database import Database

log = logging.getLogger("captacao.automacoes")
router = APIRouter(prefix="/api/automacoes", tags=["Automacoes"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


def _ensure_tables(db):
    try:
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS automacao_regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                condicao TEXT NOT NULL,
                acao TEXT NOT NULL,
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        db.conn.commit()
    except Exception:
        pass


class RegraRequest(BaseModel):
    nome: str
    tipo: str  # alerta_prazo, alerta_erro, notificacao_nova_pub, auto_classificar
    condicao: str  # JSON string com condições
    acao: str  # JSON string com ações


@router.post("/regras", summary="Criar regra de automação")
def criar_regra(req: RegraRequest):
    db = get_db()
    _ensure_tables(db)
    cur = db.conn.execute(
        "INSERT INTO automacao_regras (nome, tipo, condicao, acao) VALUES (?, ?, ?, ?)",
        (req.nome, req.tipo, req.condicao, req.acao)
    )
    db.conn.commit()
    return {"status": "success", "id": cur.lastrowid}


@router.get("/regras", summary="Listar regras de automação")
def listar_regras(ativo: Optional[bool] = Query(None)):
    db = get_db()
    _ensure_tables(db)
    if ativo is not None:
        rows = db.conn.execute("SELECT * FROM automacao_regras WHERE ativo = ? ORDER BY id DESC", (1 if ativo else 0,)).fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM automacao_regras ORDER BY id DESC").fetchall()
    return {"status": "success", "total": len(rows), "regras": [dict(r) for r in rows]}


@router.put("/regras/{regra_id}/toggle", summary="Ativar/desativar regra")
def toggle_regra(regra_id: int):
    db = get_db()
    _ensure_tables(db)
    row = db.conn.execute("SELECT ativo FROM automacao_regras WHERE id = ?", (regra_id,)).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    novo = 0 if row["ativo"] else 1
    db.conn.execute("UPDATE automacao_regras SET ativo = ? WHERE id = ?", (novo, regra_id))
    db.conn.commit()
    return {"status": "success", "ativo": bool(novo)}


@router.delete("/regras/{regra_id}", summary="Remover regra")
def remover_regra(regra_id: int):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute("DELETE FROM automacao_regras WHERE id = ?", (regra_id,))
    db.conn.commit()
    return {"status": "success"}


# =============================================================================
# Resumo de Automações
# =============================================================================

@router.get("/resumo", summary="Resumo de automações")
def resumo_automacoes():
    db = get_db()
    _ensure_tables(db)
    
    total = db.conn.execute("SELECT COUNT(*) as c FROM automacao_regras").fetchone()["c"]
    ativas = db.conn.execute("SELECT COUNT(*) as c FROM automacao_regras WHERE ativo = 1").fetchone()["c"]
    
    # Prazos vencendo
    prazos_urgentes = 0
    try:
        hoje = date.today().isoformat()
        from datetime import timedelta
        limite = (date.today() + timedelta(days=3)).isoformat()
        prazos_urgentes = db.conn.execute(
            "SELECT COUNT(*) as c FROM prazos WHERE status = 'ativo' AND data_fim >= ? AND data_fim <= ?",
            (hoje, limite)
        ).fetchone()["c"]
    except Exception:
        pass
    
    # Captações sem resultados recentes
    captacoes_alerta = 0
    try:
        captacoes_alerta = db.conn.execute("""
            SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1
            AND (ultima_execucao IS NULL OR ultima_execucao < datetime('now', 'localtime', '-24 hours'))
        """).fetchone()["c"]
    except Exception:
        pass
    
    return {
        "status": "success",
        "regras_total": total,
        "regras_ativas": ativas,
        "prazos_urgentes": prazos_urgentes,
        "captacoes_alerta": captacoes_alerta,
    }


# =============================================================================
# Histórico de Execuções de Automações
# =============================================================================

@router.get("/historico", summary="Histórico de automações executadas")
def historico_automacoes(limite: int = Query(50, ge=1, le=500)):
    db = get_db()
    try:
        rows = db.conn.execute("""
            CREATE TABLE IF NOT EXISTS automacao_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regra_id INTEGER,
                tipo TEXT,
                resultado TEXT,
                detalhes TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        db.conn.commit()
    except Exception:
        pass
    
    try:
        rows = db.conn.execute("SELECT * FROM automacao_historico ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return {"status": "success", "total": len(rows), "historico": [dict(r) for r in rows]}
    except Exception:
        return {"status": "success", "total": 0, "historico": []}
