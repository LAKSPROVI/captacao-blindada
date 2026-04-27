"""
Captacao Peticao Blindada - Analytics Router.
Endpoints de analitica e estatisticas avancadas.
"""

from fastapi import Request, APIRouter, Depends, Query
from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
import logging
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.analytics")
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


# =========================================================================
# 1. Publicacoes por dia (ultimos 30 dias)
# =========================================================================

@router.get("/publicacoes-por-dia")
@limiter.limit("60/minute")
def publicacoes_por_dia(request: Request, dias: int = Query(30, ge=1, le=365)):
    """Contagem de publicacoes por dia nos ultimos N dias."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT date(criado_em) as dia, COUNT(*) as total
            FROM publicacoes
            WHERE criado_em >= datetime('now', 'localtime', ?)
            GROUP BY date(criado_em)
            ORDER BY dia ASC
        """, (f'-{dias} days',)).fetchall()
        data = [{"dia": r["dia"], "total": r["total"]} for r in rows]
        return {"status": "success", "dias": dias, "data": data}
    except Exception as e:
        log.error("Erro publicacoes-por-dia: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 2. Publicacoes por tribunal
# =========================================================================

@router.get("/publicacoes-por-tribunal")
@limiter.limit("60/minute")
def publicacoes_por_tribunal(request: Request):
    """Contagem de publicacoes agrupadas por tribunal."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(tribunal, 'N/A') as tribunal, COUNT(*) as total
            FROM publicacoes
            GROUP BY tribunal
            ORDER BY total DESC
        """).fetchall()
        data = [{"tribunal": r["tribunal"], "total": r["total"]} for r in rows]
        return {"status": "success", "data": data}
    except Exception as e:
        log.error("Erro publicacoes-por-tribunal: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 3. Execucoes por status
# =========================================================================

@router.get("/execucoes-por-status")
@limiter.limit("60/minute")
def execucoes_por_status(request: Request):
    """Contagem de execucoes de captacao agrupadas por status."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(status, 'unknown') as status, COUNT(*) as total
            FROM execucoes_captacao
            GROUP BY status
            ORDER BY total DESC
        """).fetchall()
        data = [{"status": r["status"], "total": r["total"]} for r in rows]
        return {"status": "success", "data": data}
    except Exception as e:
        log.error("Erro execucoes-por-status: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 4. Tempo medio de execucao por captacao
# =========================================================================

@router.get("/tempo-medio-execucao")
@limiter.limit("60/minute")
def tempo_medio_execucao(request: Request):
    """Tempo medio de execucao (ms) por captacao."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT
                ec.captacao_id,
                c.nome as captacao_nome,
                COUNT(ec.id) as total_execucoes,
                CAST(AVG(ec.duracao_ms) AS INTEGER) as media_ms,
                MIN(ec.duracao_ms) as min_ms,
                MAX(ec.duracao_ms) as max_ms
            FROM execucoes_captacao ec
            LEFT JOIN captacoes c ON c.id = ec.captacao_id
            WHERE ec.duracao_ms IS NOT NULL AND ec.duracao_ms > 0
            GROUP BY ec.captacao_id
            ORDER BY media_ms DESC
        """).fetchall()
        data = [
            {
                "captacao_id": r["captacao_id"],
                "captacao_nome": r["captacao_nome"],
                "total_execucoes": r["total_execucoes"],
                "media_ms": r["media_ms"],
                "min_ms": r["min_ms"],
                "max_ms": r["max_ms"],
            }
            for r in rows
        ]
        return {"status": "success", "data": data}
    except Exception as e:
        log.error("Erro tempo-medio-execucao: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 5. Taxa de novos resultados ao longo do tempo
# =========================================================================

@router.get("/taxa-novos")
@limiter.limit("60/minute")
def taxa_novos(request: Request, dias: int = Query(30, ge=1, le=365)):
    """Taxa de novos resultados por dia nos ultimos N dias."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT date(inicio) as dia,
                   SUM(novos_resultados) as novos,
                   SUM(total_resultados) as total
            FROM execucoes_captacao
            WHERE inicio >= datetime('now', 'localtime', ?)
            GROUP BY date(inicio)
            ORDER BY dia ASC
        """, (f'-{dias} days',)).fetchall()
        data = [
            {
                "dia": r["dia"],
                "novos": r["novos"] or 0,
                "total": r["total"] or 0,
            }
            for r in rows
        ]
        return {"status": "success", "dias": dias, "data": data}
    except Exception as e:
        log.error("Erro taxa-novos: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 6. Horas de pico (distribuicao de execucoes por hora do dia)
# =========================================================================

@router.get("/horas-pico")
@limiter.limit("60/minute")
def horas_pico(request: Request):
    """Distribuicao de execucoes por hora do dia."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT CAST(strftime('%H', inicio) AS INTEGER) as hora,
                   COUNT(*) as total
            FROM execucoes_captacao
            WHERE inicio IS NOT NULL
            GROUP BY strftime('%H', inicio)
            ORDER BY hora ASC
        """).fetchall()
        data = [{"hora": r["hora"], "total": r["total"]} for r in rows]
        return {"status": "success", "data": data}
    except Exception as e:
        log.error("Erro horas-pico: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 7. Resumo mensal (execucoes, novos resultados, erros)
# =========================================================================

@router.get("/resumo-mensal")
@limiter.limit("60/minute")
def resumo_mensal(request: Request, meses: int = Query(6, ge=1, le=24)):
    """Resumo mensal: execucoes, novos resultados e erros."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT
                strftime('%Y-%m', inicio) as mes,
                COUNT(*) as total_execucoes,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as sucesso,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as erros,
                COALESCE(SUM(novos_resultados), 0) as novos_resultados,
                COALESCE(SUM(total_resultados), 0) as total_resultados
            FROM execucoes_captacao
            WHERE inicio >= datetime('now', 'localtime', ?)
            GROUP BY strftime('%Y-%m', inicio)
            ORDER BY mes ASC
        """, (f'-{meses} months',)).fetchall()
        data = [
            {
                "mes": r["mes"],
                "total_execucoes": r["total_execucoes"],
                "sucesso": r["sucesso"],
                "erros": r["erros"],
                "novos_resultados": r["novos_resultados"],
                "total_resultados": r["total_resultados"],
            }
            for r in rows
        ]
        return {"status": "success", "meses": meses, "data": data}
    except Exception as e:
        log.error("Erro resumo-mensal: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}
