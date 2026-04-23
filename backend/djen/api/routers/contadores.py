"""
Router de Contadores - CAPTAÇÃO BLINDADA.
Contadores em tempo real para sidebar e widgets.
"""
import logging
from datetime import date

from fastapi import APIRouter

from djen.api.database import Database

log = logging.getLogger("captacao.contadores")
router = APIRouter(prefix="/api/contadores", tags=["Contadores"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("", summary="Contadores em tempo real")
def contadores():
    """Retorna contadores para sidebar e widgets."""
    db = get_db()
    hoje = date.today().isoformat()
    
    captacoes = db.conn.execute("SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1").fetchone()["c"]
    publicacoes = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
    pub_hoje = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes WHERE date(data_publicacao) = ?", (hoje,)).fetchone()["c"]
    exec_hoje = db.conn.execute("SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) = ?", (hoje,)).fetchone()["c"]
    erros_abertos = db.conn.execute("SELECT COUNT(*) as c FROM system_errors WHERE status = 'aberto'").fetchone()["c"]
    
    prazos_ativos = 0
    agenda_hoje = 0
    favoritos = 0
    try:
        prazos_ativos = db.conn.execute("SELECT COUNT(*) as c FROM prazos WHERE status = 'ativo' AND data_fim >= ?", (hoje,)).fetchone()["c"]
    except Exception:
        pass
    try:
        agenda_hoje = db.conn.execute("SELECT COUNT(*) as c FROM agenda WHERE data_evento = ? AND status = 'pendente'", (hoje,)).fetchone()["c"]
    except Exception:
        pass
    try:
        favoritos = db.conn.execute("SELECT COUNT(*) as c FROM favoritos").fetchone()["c"]
    except Exception:
        pass
    
    processos = 0
    try:
        processos = db.conn.execute("SELECT COUNT(*) as c FROM processos_monitorados WHERE ativo = 1").fetchone()["c"]
    except Exception:
        pass
    
    return {
        "captacoes_ativas": captacoes,
        "publicacoes_total": publicacoes,
        "publicacoes_hoje": pub_hoje,
        "execucoes_hoje": exec_hoje,
        "erros_abertos": erros_abertos,
        "prazos_ativos": prazos_ativos,
        "agenda_hoje": agenda_hoje,
        "favoritos": favoritos,
        "processos": processos,
    }
