"""
Router de Favoritos e Tags - CAPTAÇÃO BLINDADA.
Sistema de marcadores e etiquetas.
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import Request, APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.favoritos")
router = APIRouter(prefix="/api/favoritos", tags=["Favoritos e Tags"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


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
@limiter.limit("30/minute")
def adicionar_favorito(request: Request, req: FavoritoRequest):
    db = get_db()

    try:
        cur = db.conn.execute(
            "INSERT OR IGNORE INTO favoritos (tipo, referencia_id, titulo, descricao, cor) VALUES (?, ?, ?, ?, ?)",
            (req.tipo, req.referencia_id, req.titulo, req.descricao, req.cor)
        )
        db.conn.commit()
        return {"status": "success", "id": cur.lastrowid}
    except Exception as e:
        log.error("Erro ao adicionar favorito: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Erro ao adicionar favorito")


@router.delete("/{tipo}/{referencia_id}", summary="Remover favorito")
@limiter.limit("30/minute")
def remover_favorito(request: Request, tipo: str, referencia_id: int):
    db = get_db()

    db.conn.execute("DELETE FROM favoritos WHERE tipo = ? AND referencia_id = ?", (tipo, referencia_id))
    db.conn.commit()
    return {"status": "success"}


@router.get("", summary="Listar favoritos")
@limiter.limit("60/minute")
def listar_favoritos(request: Request, tipo: Optional[str] = Query(None), limite: int = Query(100, ge=1, le=500)):
    db = get_db()

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
@limiter.limit("30/minute")
def criar_tag(request: Request, req: TagRequest):
    db = get_db()

    try:
        cur = db.conn.execute("INSERT OR IGNORE INTO tags (nome, cor) VALUES (?, ?)", (req.nome, req.cor))
        db.conn.commit()
        return {"status": "success", "id": cur.lastrowid, "nome": req.nome}
    except Exception as e:
        log.error("Erro ao criar tag: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Erro ao criar tag")


@router.get("/tags", summary="Listar tags")
@limiter.limit("60/minute")
def listar_tags(request: Request):
    db = get_db()

    rows = db.conn.execute("SELECT * FROM tags ORDER BY nome").fetchall()
    return {"status": "success", "total": len(rows), "tags": [dict(r) for r in rows]}


@router.delete("/tags/{tag_id}", summary="Remover tag")
@limiter.limit("30/minute")
def remover_tag(request: Request, tag_id: int):
    db = get_db()

    db.conn.execute("DELETE FROM tag_associacoes WHERE tag_id = ?", (tag_id,))
    db.conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    db.conn.commit()
    return {"status": "success"}


@router.post("/tags/{tag_id}/associar", summary="Associar tag a item")
@limiter.limit("30/minute")
def associar_tag(request: Request, tag_id: int, tipo: str = Body(...), referencia_id: int = Body(...)):
    db = get_db()

    db.conn.execute(
        "INSERT OR IGNORE INTO tag_associacoes (tag_id, tipo, referencia_id) VALUES (?, ?, ?)",
        (tag_id, tipo, referencia_id)
    )
    db.conn.commit()
    return {"status": "success"}


@router.delete("/tags/{tag_id}/desassociar/{tipo}/{referencia_id}", summary="Desassociar tag")
@limiter.limit("30/minute")
def desassociar_tag(request: Request, tag_id: int, tipo: str, referencia_id: int):
    db = get_db()

    db.conn.execute(
        "DELETE FROM tag_associacoes WHERE tag_id = ? AND tipo = ? AND referencia_id = ?",
        (tag_id, tipo, referencia_id)
    )
    db.conn.commit()
    return {"status": "success"}


@router.get("/tags/item/{tipo}/{referencia_id}", summary="Tags de um item")
@limiter.limit("60/minute")
def tags_do_item(request: Request, tipo: str, referencia_id: int):
    db = get_db()

    rows = db.conn.execute("""
        SELECT t.* FROM tags t
        JOIN tag_associacoes ta ON t.id = ta.tag_id
        WHERE ta.tipo = ? AND ta.referencia_id = ?
    """, (tipo, referencia_id)).fetchall()
    return {"status": "success", "total": len(rows), "tags": [dict(r) for r in rows]}
