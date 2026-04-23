"""
Router de Busca Global - CAPTAÇÃO BLINDADA.
Busca full-text em todo o sistema.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query

from djen.api.database import Database

log = logging.getLogger("captacao.busca_global")
router = APIRouter(prefix="/api/busca-global", tags=["Busca Global"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("", summary="Busca global no sistema")
def busca_global(
    q: str = Query(..., min_length=2, description="Termo de busca"),
    limite: int = Query(50, ge=1, le=200),
):
    """Busca full-text em publicações, processos, captações e anotações."""
    db = get_db()
    termo = f"%{q}%"
    resultados = {"publicacoes": [], "captacoes": [], "processos": [], "anotacoes": []}
    
    # Publicações
    try:
        rows = db.conn.execute("""
            SELECT id, fonte, tribunal, numero_processo, data_publicacao, 
                   substr(conteudo, 1, 200) as conteudo_resumo
            FROM publicacoes 
            WHERE conteudo LIKE ? OR numero_processo LIKE ? OR advogados LIKE ? OR partes LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (termo, termo, termo, termo, limite)).fetchall()
        resultados["publicacoes"] = [dict(r) for r in rows]
    except Exception:
        pass
    
    # Captações
    try:
        rows = db.conn.execute("""
            SELECT id, nome, tipo_busca, numero_oab, nome_parte, nome_advogado, ativo
            FROM captacoes 
            WHERE nome LIKE ? OR numero_oab LIKE ? OR nome_parte LIKE ? OR nome_advogado LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (termo, termo, termo, termo, limite)).fetchall()
        resultados["captacoes"] = [dict(r) for r in rows]
    except Exception:
        pass
    
    # Processos monitorados
    try:
        rows = db.conn.execute("""
            SELECT id, numero_processo, tribunal, ativo
            FROM processos_monitorados 
            WHERE numero_processo LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (termo, limite)).fetchall()
        resultados["processos"] = [dict(r) for r in rows]
    except Exception:
        pass
    
    # Anotações
    try:
        rows = db.conn.execute("""
            SELECT id, numero_processo, texto, tipo, criado_em
            FROM processo_anotacoes 
            WHERE texto LIKE ? OR numero_processo LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (termo, termo, limite)).fetchall()
        resultados["anotacoes"] = [dict(r) for r in rows]
    except Exception:
        pass
    
    total = sum(len(v) for v in resultados.values())
    
    return {
        "status": "success",
        "query": q,
        "total": total,
        "resultados": resultados,
    }
