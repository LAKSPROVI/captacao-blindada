"""
Router de Relatórios - CAPTAÇÃO BLINDADA.
Geração de relatórios automáticos.
"""
import logging
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.relatorios")
router = APIRouter(prefix="/api/relatorios", tags=["Relatorios"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("/semanal", summary="Relatório semanal")
@limiter.limit("60/minute")
def relatorio_semanal(request: Request):
    """Gera relatório semanal com resumo de atividades."""
    db = get_db()
    
    captacoes = db.conn.execute(
        "SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1"
    ).fetchone()["c"]
    
    execucoes = db.conn.execute(
        "SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) >= date('now', 'localtime', '-7 days')"
    ).fetchone()["c"]
    
    novos = db.conn.execute(
        "SELECT COALESCE(SUM(novos_resultados), 0) as t FROM execucoes_captacao WHERE date(inicio) >= date('now', 'localtime', '-7 days')"
    ).fetchone()["t"]
    
    publicacoes = db.conn.execute(
        "SELECT COUNT(*) as c FROM publicacoes WHERE date(data_publicacao) >= date('now', 'localtime', '-7 days')"
    ).fetchone()["c"]
    
    erros = db.conn.execute(
        "SELECT COUNT(*) as c FROM system_errors WHERE date(criado_em) >= date('now', 'localtime', '-7 days')"
    ).fetchone()["c"]
    
    top_tribunais = db.conn.execute(
        """SELECT tribunal, COUNT(*) as c FROM publicacoes 
           WHERE date(data_publicacao) >= date('now', 'localtime', '-7 days') AND tribunal IS NOT NULL
           GROUP BY tribunal ORDER BY c DESC LIMIT 10"""
    ).fetchall()
    
    ultimas_exec = db.conn.execute(
        """SELECT e.id, e.captacao_id, e.inicio, e.status, e.total_resultados, e.novos_resultados, c.nome
           FROM execucoes_captacao e JOIN captacoes c ON e.captacao_id = c.id
           WHERE date(e.inicio) >= date('now', 'localtime', '-7 days')
           ORDER BY e.inicio DESC LIMIT 20"""
    ).fetchall()
    
    return {
        "periodo": f"{(datetime.now() - timedelta(days=7)).strftime('%d/%m/%Y')} a {datetime.now().strftime('%d/%m/%Y')}",
        "gerado_em": datetime.now().isoformat(),
        "resumo": {
            "captacoes_ativas": captacoes,
            "execucoes_semana": execucoes,
            "novos_resultados": novos,
            "publicacoes_semana": publicacoes,
            "erros_semana": erros,
        },
        "top_tribunais": [{"tribunal": r["tribunal"], "total": r["c"]} for r in top_tribunais],
        "ultimas_execucoes": [dict(r) for r in ultimas_exec],
    }


@router.get("/semanal/csv", summary="Relatório semanal em CSV")
@limiter.limit("60/minute")
def relatorio_semanal_csv(request: Request):
    """Exporta relatório semanal em CSV."""
    db = get_db()
    
    rows = db.conn.execute(
        """SELECT e.id, c.nome, e.inicio, e.status, e.total_resultados, e.novos_resultados, e.duracao_ms
           FROM execucoes_captacao e JOIN captacoes c ON e.captacao_id = c.id
           WHERE date(e.inicio) >= date('now', 'localtime', '-7 days')
           ORDER BY e.inicio DESC"""
    ).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Captação", "Início", "Status", "Total", "Novos", "Duração (ms)"])
    for r in rows:
        writer.writerow([r["id"], r["nome"], r["inicio"], r["status"], r["total_resultados"], r["novos_resultados"], r["duracao_ms"]])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=relatorio_semanal_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@router.get("/diario", summary="Relatório diário")
@limiter.limit("60/minute")
def relatorio_diario(request: Request):
    """Gera relatório do dia atual."""
    db = get_db()
    
    execucoes = db.conn.execute(
        "SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) = date('now', 'localtime')"
    ).fetchone()["c"]
    
    novos = db.conn.execute(
        "SELECT COALESCE(SUM(novos_resultados), 0) as t FROM execucoes_captacao WHERE date(inicio) = date('now', 'localtime')"
    ).fetchone()["t"]
    
    publicacoes = db.conn.execute(
        "SELECT COUNT(*) as c FROM publicacoes WHERE date(data_publicacao) = date('now', 'localtime')"
    ).fetchone()["c"]
    
    erros = db.conn.execute(
        "SELECT COUNT(*) as c FROM system_errors WHERE date(criado_em) = date('now', 'localtime')"
    ).fetchone()["c"]
    
    return {
        "data": datetime.now().strftime("%d/%m/%Y"),
        "gerado_em": datetime.now().isoformat(),
        "execucoes_hoje": execucoes,
        "novos_resultados": novos,
        "publicacoes_hoje": publicacoes,
        "erros_hoje": erros,
    }
