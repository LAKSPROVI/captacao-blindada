"""
Router de Favoritos e Tags - CAPTAÇÃO BLINDADA.
Sistema de marcadores e etiquetas.
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from djen.api.database import Database

log = logging.getLogger("captacao.favoritos")
router = APIRouter(prefix="/api/favoritos", tags=["Favoritos e Tags"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


def _ensure_tables(db):
    try:
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS favoritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                referencia_id INTEGER NOT NULL,
                titulo TEXT,
                descricao TEXT,
                cor TEXT DEFAULT '#3b82f6',
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(tipo, referencia_id)
            )
        """)
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                cor TEXT DEFAULT '#6b7280',
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS tag_associacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                referencia_id INTEGER NOT NULL,
                UNIQUE(tag_id, tipo, referencia_id)
            )
        """)
        db.conn.commit()
    except Exception:
        pass


# =============================================================================
# Favoritos
# =============================================================================

class FavoritoRequest(BaseModel):
    tipo: str  # publicacao, processo, captacao
    referencia_id: int
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    cor: Optional[str] = "#3b82f6"


@router.post("", summary="Adicionar favorito")
def adicionar_favorito(req: FavoritoRequest):
    db = get_db()
    _ensure_tables(db)
    try:
        cur = db.conn.execute(
            "INSERT OR IGNORE INTO favoritos (tipo, referencia_id, titulo, descricao, cor) VALUES (?, ?, ?, ?, ?)",
            (req.tipo, req.referencia_id, req.titulo, req.descricao, req.cor)
        )
        db.conn.commit()
        return {"status": "success", "id": cur.lastrowid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tipo}/{referencia_id}", summary="Remover favorito")
def remover_favorito(tipo: str, referencia_id: int):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute("DELETE FROM favoritos WHERE tipo = ? AND referencia_id = ?", (tipo, referencia_id))
    db.conn.commit()
    return {"status": "success"}


@router.get("", summary="Listar favoritos")
def listar_favoritos(tipo: Optional[str] = Query(None), limite: int = Query(100, ge=1, le=500)):
    db = get_db()
    _ensure_tables(db)
    if tipo:
        rows = db.conn.execute("SELECT * FROM favoritos WHERE tipo = ? ORDER BY criado_em DESC LIMIT ?", (tipo, limite)).fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM favoritos ORDER BY criado_em DESC LIMIT ?", (limite,)).fetchall()
    return {"status": "success", "total": len(rows), "favoritos": [dict(r) for r in rows]}


# =============================================================================
# Tags
# =============================================================================

class TagRequest(BaseModel):
    nome: str
    cor: Optional[str] = "#6b7280"


@router.post("/tags", summary="Criar tag")
def criar_tag(req: TagRequest):
    db = get_db()
    _ensure_tables(db)
    try:
        cur = db.conn.execute("INSERT OR IGNORE INTO tags (nome, cor) VALUES (?, ?)", (req.nome, req.cor))
        db.conn.commit()
        return {"status": "success", "id": cur.lastrowid, "nome": req.nome}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tags", summary="Listar tags")
def listar_tags():
    db = get_db()
    _ensure_tables(db)
    rows = db.conn.execute("SELECT * FROM tags ORDER BY nome").fetchall()
    return {"status": "success", "total": len(rows), "tags": [dict(r) for r in rows]}


@router.delete("/tags/{tag_id}", summary="Remover tag")
def remover_tag(tag_id: int):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute("DELETE FROM tag_associacoes WHERE tag_id = ?", (tag_id,))
    db.conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    db.conn.commit()
    return {"status": "success"}


@router.post("/tags/{tag_id}/associar", summary="Associar tag a item")
def associar_tag(tag_id: int, tipo: str = Body(...), referencia_id: int = Body(...)):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute(
        "INSERT OR IGNORE INTO tag_associacoes (tag_id, tipo, referencia_id) VALUES (?, ?, ?)",
        (tag_id, tipo, referencia_id)
    )
    db.conn.commit()
    return {"status": "success"}


@router.delete("/tags/{tag_id}/desassociar/{tipo}/{referencia_id}", summary="Desassociar tag")
def desassociar_tag(tag_id: int, tipo: str, referencia_id: int):
    db = get_db()
    _ensure_tables(db)
    db.conn.execute(
        "DELETE FROM tag_associacoes WHERE tag_id = ? AND tipo = ? AND referencia_id = ?",
        (tag_id, tipo, referencia_id)
    )
    db.conn.commit()
    return {"status": "success"}


@router.get("/tags/item/{tipo}/{referencia_id}", summary="Tags de um item")
def tags_do_item(tipo: str, referencia_id: int):
    db = get_db()
    _ensure_tables(db)
    rows = db.conn.execute("""
        SELECT t.* FROM tags t
        JOIN tag_associacoes ta ON t.id = ta.tag_id
        WHERE ta.tipo = ? AND ta.referencia_id = ?
    """, (tipo, referencia_id)).fetchall()
    return {"status": "success", "total": len(rows), "tags": [dict(r) for r in rows]}
