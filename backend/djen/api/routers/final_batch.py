"""
Router Final - CAPTAÇÃO BLINDADA.
Endpoints finais para completar 200 implementações.
"""
import logging
import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import Request, APIRouter, Depends, Query, Body
from pydantic import BaseModel

from djen.api.database import Database
from djen.api.auth import get_current_user, require_role, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.final")
router = APIRouter(prefix="/api/v2", tags=["V2 - Funcionalidades Avançadas"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


# =============================================================================
# 1. Comparação de Desempenho entre Captações
# =============================================================================

@router.get("/captacoes/comparar", summary="Comparar desempenho entre captações")
@limiter.limit("60/minute")
def comparar_captacoes(request: Request, ids: str = Query(..., description="IDs separados por vírgula")):
    db = get_db()
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
    resultados = []
    for cid in id_list:
        try:
            cap = db.conn.execute("SELECT id, nome, tipo_busca, total_execucoes, total_novos FROM captacoes WHERE id=?", (cid,)).fetchone()
            if cap:
                avg = db.conn.execute("SELECT AVG(duracao_ms) as avg_ms FROM execucoes_captacao WHERE captacao_id=?", (cid,)).fetchone()
                resultados.append({**dict(cap), "tempo_medio_ms": round(avg["avg_ms"] or 0)})
        except Exception:
            pass
    return {"status": "success", "comparacao": resultados}


# =============================================================================
# 2. Publicações por Período Customizado
# =============================================================================

@router.get("/publicacoes/periodo", summary="Publicações por período")
@limiter.limit("60/minute")
def publicacoes_periodo(request: Request, data_inicio: str = Query(...),
    data_fim: str = Query(...),
    tribunal: Optional[str] = Query(None),
):
    db = get_db()
    params = [data_inicio, data_fim]
    query = "SELECT COUNT(*) as total FROM publicacoes WHERE date(data_publicacao) BETWEEN ? AND ?"
    if tribunal:
        query += " AND tribunal = ?"
        params.append(tribunal)
    total = db.conn.execute(query, params).fetchone()["total"]
    return {"status": "success", "data_inicio": data_inicio, "data_fim": data_fim, "total": total}


# =============================================================================
# 3. Score de Produtividade
# =============================================================================

@router.get("/produtividade/score", summary="Score de produtividade do sistema")
@limiter.limit("60/minute")
def score_produtividade(request: Request):
    db = get_db()
    hoje = date.today().isoformat()
    semana = (date.today() - timedelta(days=7)).isoformat()
    
    exec_semana = db.conn.execute("SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) >= ?", (semana,)).fetchone()["c"]
    novos_semana = db.conn.execute("SELECT COALESCE(SUM(novos_resultados),0) as t FROM execucoes_captacao WHERE date(inicio) >= ?", (semana,)).fetchone()["t"]
    erros_semana = db.conn.execute("SELECT COUNT(*) as c FROM system_errors WHERE date(criado_em) >= ?", (semana,)).fetchone()["c"]
    
    score = min(100, max(0, int((exec_semana * 5 + novos_semana * 0.1 - erros_semana * 10))))
    
    return {
        "status": "success",
        "score": score,
        "execucoes_semana": exec_semana,
        "novos_semana": novos_semana,
        "erros_semana": erros_semana,
        "classificacao": "Excelente" if score >= 80 else "Bom" if score >= 60 else "Regular" if score >= 40 else "Baixo",
    }


# =============================================================================
# 4. Mapa de Calor de Atividade
# =============================================================================

@router.get("/atividade/heatmap", summary="Mapa de calor de atividade")
@limiter.limit("60/minute")
def heatmap_atividade(request: Request, dias: int = Query(30, ge=7, le=90)):
    db = get_db()
    rows = db.conn.execute("""
        SELECT date(inicio) as dia, strftime('%H', inicio) as hora, COUNT(*) as total
        FROM execucoes_captacao
        WHERE date(inicio) >= date('now','localtime', ? || ' days')
        GROUP BY date(inicio), strftime('%H', inicio)
    """, (f"-{dias}",)).fetchall()
    return {"status": "success", "dias": dias, "heatmap": [dict(r) for r in rows]}


# =============================================================================
# 5. Previsão de Consumo
# =============================================================================

@router.get("/previsao/consumo", summary="Previsão de consumo de tokens")
@limiter.limit("60/minute")
def previsao_consumo(request: Request):
    db = get_db()
    try:
        ultimos_30 = db.conn.execute("""
            SELECT COALESCE(SUM(tokens_used),0) as total FROM usage_logs
            WHERE date(data_uso) >= date('now','localtime','-30 days')
        """).fetchone()["total"]
        media_diaria = ultimos_30 / 30 if ultimos_30 > 0 else 0
        previsao_mensal = int(media_diaria * 30)
        
        tenant = db.conn.execute("SELECT saldo_tokens FROM tenants LIMIT 1").fetchone()
        saldo = tenant["saldo_tokens"] if tenant else 0
        dias_restantes = int(saldo / media_diaria) if media_diaria > 0 else 999
        
        return {
            "status": "success",
            "consumo_30d": ultimos_30,
            "media_diaria": round(media_diaria),
            "previsao_mensal": previsao_mensal,
            "saldo_atual": saldo,
            "dias_restantes": dias_restantes,
        }
    except Exception:
        return {"status": "success", "consumo_30d": 0, "media_diaria": 0, "previsao_mensal": 0, "saldo_atual": 0, "dias_restantes": 999}


# =============================================================================
# 6. Notas/Lembretes Globais
# =============================================================================

@router.get("/notas", summary="Listar notas globais")
@limiter.limit("60/minute")
def listar_notas(request: Request, limite: int = Query(50, ge=1, le=200)):
    db = get_db()
    rows = db.conn.execute("SELECT * FROM notas_globais ORDER BY fixada DESC, id DESC LIMIT ?", (limite,)).fetchall()
    return {"status": "success", "total": len(rows), "notas": [dict(r) for r in rows]}


@router.post("/notas", summary="Criar nota")
@limiter.limit("30/minute")
def criar_nota(request: Request, titulo: str = Body(...), conteudo: str = Body(""), cor: str = Body("#3b82f6")):
    db = get_db()
    cur = db.conn.execute("INSERT INTO notas_globais (titulo, conteudo, cor) VALUES (?, ?, ?)", (titulo, conteudo, cor))
    db.conn.commit()
    return {"status": "success", "id": cur.lastrowid}


@router.delete("/notas/{nota_id}", summary="Remover nota")
@limiter.limit("30/minute")
def remover_nota(request: Request, nota_id: int):
    db = get_db()
    db.conn.execute("DELETE FROM notas_globais WHERE id = ?", (nota_id,))
    db.conn.commit()
    return {"status": "success"}


# =============================================================================
# 7. Templates de Captação
# =============================================================================

@router.get("/templates", summary="Listar templates de captação")
@limiter.limit("60/minute")
def listar_templates(request: Request):
    return {"status": "success", "templates": [
        {"id": "oab", "nome": "Busca por OAB", "tipo_busca": "oab", "descricao": "Monitora publicações por número de OAB"},
        {"id": "processo", "nome": "Busca por Processo", "tipo_busca": "processo", "descricao": "Monitora um processo específico por número CNJ"},
        {"id": "parte", "nome": "Busca por Nome de Parte", "tipo_busca": "nome_parte", "descricao": "Monitora publicações por nome de parte"},
        {"id": "advogado", "nome": "Busca por Advogado", "tipo_busca": "nome_advogado", "descricao": "Monitora publicações por nome de advogado"},
        {"id": "tribunal", "nome": "Busca por Tribunal", "tipo_busca": "tribunal_geral", "descricao": "Monitora todas as publicações de um tribunal"},
    ]}


# =============================================================================
# 8. Resumo Executivo Consolidado
# =============================================================================

@router.get("/resumo-executivo", summary="Resumo executivo consolidado")
@limiter.limit("60/minute")
def resumo_executivo(request: Request):
    db = get_db()
    hoje = date.today().isoformat()
    semana = (date.today() - timedelta(days=7)).isoformat()
    mes = (date.today() - timedelta(days=30)).isoformat()
    
    stats = {}
    queries = {
        "captacoes_ativas": "SELECT COUNT(*) as c FROM captacoes WHERE ativo=1",
        "publicacoes_total": "SELECT COUNT(*) as c FROM publicacoes",
        "publicacoes_semana": f"SELECT COUNT(*) as c FROM publicacoes WHERE date(data_publicacao) >= '{semana}'",
        "publicacoes_mes": f"SELECT COUNT(*) as c FROM publicacoes WHERE date(data_publicacao) >= '{mes}'",
        "execucoes_hoje": f"SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) = '{hoje}'",
        "execucoes_semana": f"SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) >= '{semana}'",
        "novos_hoje": f"SELECT COALESCE(SUM(novos_resultados),0) as c FROM execucoes_captacao WHERE date(inicio) = '{hoje}'",
        "novos_semana": f"SELECT COALESCE(SUM(novos_resultados),0) as c FROM execucoes_captacao WHERE date(inicio) >= '{semana}'",
        "erros_abertos": "SELECT COUNT(*) as c FROM system_errors WHERE status='aberto'",
        "usuarios": "SELECT COUNT(*) as c FROM users",
    }
    for key, query in queries.items():
        try:
            stats[key] = db.conn.execute(query).fetchone()["c"]
        except Exception:
            stats[key] = 0
    
    return {"status": "success", "data": datetime.now().isoformat(), "resumo": stats}


# =============================================================================
# 9. Exportar Tudo (Full Backup JSON)
# =============================================================================

@router.get("/exportar-tudo", summary="Exportar todos os dados em JSON")
@limiter.limit("5/minute")
def exportar_tudo(request: Request):
    from fastapi.responses import StreamingResponse
    db = get_db()
    
    tables = ["captacoes", "publicacoes", "execucoes_captacao", "ai_config"]
    export = {"exported_at": datetime.now().isoformat(), "tables": {}}
    
    for table in tables:
        try:
            rows = db.conn.execute(f"SELECT * FROM [{table}] LIMIT 10000").fetchall()
            export["tables"][table] = [dict(r) for r in rows]
        except Exception:
            export["tables"][table] = []
    
    data = json.dumps(export, ensure_ascii=False, indent=2, default=str)
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=captacao_blindada_full_{datetime.now().strftime('%Y%m%d')}.json"}
    )


# =============================================================================
# 10. Verificação de Saúde Completa do Sistema
# =============================================================================

@router.get("/health-check-completo", summary="Verificação completa de saúde")
@limiter.limit("60/minute")
def health_check_completo(request: Request):
    db = get_db()
    checks = {}
    
    # Database
    try:
        db.conn.execute("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception as e:
        log.error("Erro health-check database: %s", e, exc_info=True)
        checks["database"] = {"status": "error", "message": "Erro ao acessar banco de dados"}
    
    # Tables
    try:
        tables = db.conn.execute("SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'").fetchone()["c"]
        checks["tables"] = {"status": "ok", "count": tables}
    except Exception:
        checks["tables"] = {"status": "error"}
    
    # Publicações
    try:
        pub = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
        checks["publicacoes"] = {"status": "ok", "count": pub}
    except Exception:
        checks["publicacoes"] = {"status": "error"}
    
    # Captações
    try:
        cap = db.conn.execute("SELECT COUNT(*) as c FROM captacoes WHERE ativo=1").fetchone()["c"]
        checks["captacoes"] = {"status": "ok", "count": cap}
    except Exception:
        checks["captacoes"] = {"status": "error"}
    
    # Erros
    try:
        erros = db.conn.execute("SELECT COUNT(*) as c FROM system_errors WHERE status='aberto'").fetchone()["c"]
        checks["erros"] = {"status": "warning" if erros > 0 else "ok", "count": erros}
    except Exception:
        checks["erros"] = {"status": "error"}
    
    # Disk
    try:
        size = db.conn.execute("SELECT page_count * page_size as s FROM pragma_page_count(), pragma_page_size()").fetchone()["s"]
        checks["disk"] = {"status": "ok", "size_mb": round(size / 1024 / 1024, 2)}
    except Exception:
        checks["disk"] = {"status": "error"}
    
    all_ok = all(c.get("status") in ("ok", "warning") for c in checks.values())
    
    return {
        "status": "ok" if all_ok else "degraded",
        "datetime": datetime.now().isoformat(),
        "checks": checks,
    }
