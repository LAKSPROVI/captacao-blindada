"""
Router de Dashboard - CAPTAÇÃO BLINDADA.
Endpoints para dados de gráficos e evolução.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, APIRouter, Depends, Query

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("/evolucao", summary="Evolução diária de publicações")
@limiter.limit("60/minute")
def evolucao_diaria(request: Request, dias: int = Query(30, ge=1, le=90)):
    """Retorna evolução diária de publicações encontradas."""
    db = get_db()
    rows = db.conn.execute("""
        SELECT date(inicio) as dia, 
               COUNT(*) as execucoes,
               COALESCE(SUM(total_resultados), 0) as total,
               COALESCE(SUM(novos_resultados), 0) as novos
        FROM execucoes_captacao 
        WHERE date(inicio) >= date('now', 'localtime', ? || ' days')
        GROUP BY date(inicio)
        ORDER BY dia ASC
    """, (f"-{dias}",)).fetchall()
    return {"status": "success", "dias": dias, "evolucao": [dict(r) for r in rows]}


@router.get("/tribunais", summary="Distribuição por tribunal")
@limiter.limit("60/minute")
def distribuicao_tribunais(request: Request):
    """Retorna distribuição de publicações por tribunal."""
    db = get_db()
    rows = db.conn.execute("""
        SELECT tribunal, COUNT(*) as total
        FROM publicacoes 
        WHERE tribunal IS NOT NULL AND tribunal != ''
        GROUP BY tribunal
        ORDER BY total DESC
        LIMIT 20
    """).fetchall()
    return {"status": "success", "tribunais": [dict(r) for r in rows]}


@router.get("/fontes", summary="Status de todas as fontes")
@limiter.limit("60/minute")
def status_fontes(request: Request):
    """Retorna status de todas as fontes de dados."""
    db = get_db()
    
    fontes_stats = []
    try:
        fontes_stats = db.conn.execute("""
            SELECT fonte, COUNT(*) as total,
                   MAX(data_publicacao) as ultima
            FROM publicacoes
            WHERE fonte IS NOT NULL
            GROUP BY fonte
        """).fetchall()
    except Exception:
        pass
    
    buscas_stats = []
    try:
        buscas_stats = db.conn.execute("""
            SELECT fonte, COUNT(*) as total_buscas,
                   SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) as sucesso,
                   SUM(CASE WHEN status != 'ok' THEN 1 ELSE 0 END) as falhas,
                   AVG(tempo_ms) as tempo_medio_ms
            FROM buscas
            GROUP BY fonte
        """).fetchall()
    except Exception:
        pass
    
    return {
        "status": "success",
        "fontes_publicacoes": [dict(r) for r in fontes_stats],
        "fontes_buscas": [dict(r) for r in buscas_stats],
    }


@router.get("/proximas-execucoes", summary="Próximas execuções agendadas")
@limiter.limit("60/minute")
def proximas_execucoes(request: Request):
    """Retorna próximas execuções agendadas."""
    db = get_db()
    rows = db.conn.execute("""
        SELECT id, nome, proxima_execucao, intervalo_minutos, tipo_busca
        FROM captacoes
        WHERE ativo = 1 AND proxima_execucao IS NOT NULL
        ORDER BY proxima_execucao ASC
        LIMIT 10
    """).fetchall()
    return {"status": "success", "proximas": [dict(r) for r in rows]}


@router.get("/atividade-recente", summary="Atividade recente do sistema")
@limiter.limit("60/minute")
def atividade_recente(request: Request, limite: int = Query(20, ge=1, le=100)):
    """Retorna atividade recente (execuções, erros, etc)."""
    db = get_db()
    
    execucoes = db.conn.execute("""
        SELECT e.id, e.captacao_id, c.nome, e.inicio, e.status, 
               e.total_resultados, e.novos_resultados, e.duracao_ms
        FROM execucoes_captacao e
        JOIN captacoes c ON e.captacao_id = c.id
        ORDER BY e.inicio DESC
        LIMIT ?
    """, (limite,)).fetchall()
    
    erros = db.conn.execute("""
        SELECT id, function_name, error_type, error_message, criado_em
        FROM system_errors
        ORDER BY id DESC
        LIMIT ?
    """, (limite,)).fetchall()
    
    return {
        "status": "success",
        "execucoes": [dict(r) for r in execucoes],
        "erros": [dict(r) for r in erros],
    }


@router.get("/resumo-completo", summary="Resumo completo do sistema")
@limiter.limit("60/minute")
def resumo_completo(request: Request):
    """Retorna resumo completo para o dashboard."""
    db = get_db()
    
    captacoes = db.conn.execute("SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1").fetchone()["c"]
    publicacoes = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
    pub_hoje = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes WHERE date(data_publicacao) = date('now', 'localtime')").fetchone()["c"]
    exec_hoje = db.conn.execute("SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) = date('now', 'localtime')").fetchone()["c"]
    novos_hoje = db.conn.execute("SELECT COALESCE(SUM(novos_resultados), 0) as t FROM execucoes_captacao WHERE date(inicio) = date('now', 'localtime')").fetchone()["t"]
    processos = 0
    try:
        processos = db.conn.execute("SELECT COUNT(*) as c FROM processos_monitorados WHERE ativo = 1").fetchone()["c"]
    except Exception:
        pass
    erros_hoje = db.conn.execute("SELECT COUNT(*) as c FROM system_errors WHERE date(criado_em) = date('now', 'localtime')").fetchone()["c"]
    
    return {
        "status": "success",
        "data": datetime.now().isoformat(),
        "captacoes_ativas": captacoes,
        "publicacoes_total": publicacoes,
        "publicacoes_hoje": pub_hoje,
        "execucoes_hoje": exec_hoje,
        "novos_hoje": novos_hoje,
        "processos_monitorados": processos,
        "erros_hoje": erros_hoje,
    }


@router.get("/comparacao-tribunais", summary="Comparação entre tribunais")
@limiter.limit("60/minute")
def comparacao_tribunais(request: Request):
    """Compara volume de publicações entre tribunais com dados semanal e mensal."""
    db = get_db()
    rows = db.conn.execute("""
        SELECT tribunal, COUNT(*) as total,
               COUNT(CASE WHEN date(data_publicacao) >= date('now','localtime','-7 days') THEN 1 END) as semana,
               COUNT(CASE WHEN date(data_publicacao) >= date('now','localtime','-30 days') THEN 1 END) as mes
        FROM publicacoes
        WHERE tribunal IS NOT NULL AND tribunal != ''
        GROUP BY tribunal
        ORDER BY total DESC
        LIMIT 20
    """).fetchall()
    return {"status": "success", "total_tribunais": len(rows), "tribunais": [dict(r) for r in rows]}


@router.get("/top-processos", summary="Processos mais ativos")
@limiter.limit("60/minute")
def top_processos(request: Request, limite: int = Query(20, ge=1, le=100)):
    """Lista processos com mais publicações."""
    db = get_db()
    rows = db.conn.execute("""
        SELECT numero_processo, tribunal, COUNT(*) as total_publicacoes,
               MAX(data_publicacao) as ultima_publicacao,
               GROUP_CONCAT(DISTINCT fonte) as fontes
        FROM publicacoes
        WHERE numero_processo IS NOT NULL AND numero_processo != ''
        GROUP BY numero_processo
        ORDER BY total_publicacoes DESC
        LIMIT ?
    """, (limite,)).fetchall()
    return {"status": "success", "total": len(rows), "processos": [dict(r) for r in rows]}
