"""
Captacao Peticao Blindada - Extras Router.
Endpoints utilitarios: batch insert, agrupamentos, limpeza e saude completa.
"""

import logging
import time
from typing import Optional, List

from fastapi import Request, APIRouter, Depends, Query, Body
from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.extras")
router = APIRouter(prefix="/api/extras", tags=["Extras"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


# =========================================================================
# 1. Batch insert de publicacoes
# =========================================================================

@router.post("/batch-insert-publicacoes")
@limiter.limit("30/minute")
def batch_insert_publicacoes(request: Request, publicacoes: List[dict] = Body(..., embed=False)):
    """Insere multiplas publicacoes de uma vez. Recebe lista de dicts de publicacao."""
    try:
        db = get_db()
        inseridos = 0
        ignorados = 0
        erros = 0
        for pub in publicacoes:
            try:
                result = db.salvar_publicacao(pub)
                if result:
                    inseridos += 1
                else:
                    ignorados += 1
            except Exception:
                erros += 1
        return {
            "status": "success",
            "total_recebidos": len(publicacoes),
            "inseridos": inseridos,
            "ignorados": ignorados,
            "erros": erros,
        }
    except Exception as e:
        log.error("Erro batch-insert-publicacoes: %s", e)
        return {"status": "error", "message": "Erro ao inserir publicacoes em lote"}


# =========================================================================
# 2. Publicacoes por classe processual
# =========================================================================

@router.get("/publicacoes-por-classe")
@limiter.limit("60/minute")
def publicacoes_por_classe(request: Request, limite: int = Query(50, ge=1, le=500)):
    """Agrupa publicacoes por classe_processual."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(classe_processual, 'N/A') as classe_processual,
                   COUNT(*) as total
            FROM publicacoes
            GROUP BY classe_processual
            ORDER BY total DESC
            LIMIT ?
        """, (limite,)).fetchall()
        data = [{"classe_processual": r["classe_processual"], "total": r["total"]} for r in rows]
        return {"status": "success", "total_classes": len(data), "data": data}
    except Exception as e:
        log.error("Erro publicacoes-por-classe: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 3. Publicacoes por orgao julgador
# =========================================================================

@router.get("/publicacoes-por-orgao")
@limiter.limit("60/minute")
def publicacoes_por_orgao(request: Request, limite: int = Query(50, ge=1, le=500)):
    """Agrupa publicacoes por orgao_julgador."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(orgao_julgador, 'N/A') as orgao_julgador,
                   COUNT(*) as total
            FROM publicacoes
            GROUP BY orgao_julgador
            ORDER BY total DESC
            LIMIT ?
        """, (limite,)).fetchall()
        data = [{"orgao_julgador": r["orgao_julgador"], "total": r["total"]} for r in rows]
        return {"status": "success", "total_orgaos": len(data), "data": data}
    except Exception as e:
        log.error("Erro publicacoes-por-orgao: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 4. Captacoes por tipo de busca
# =========================================================================

@router.get("/captacoes-por-tipo")
@limiter.limit("60/minute")
def captacoes_por_tipo(request: Request):
    """Agrupa captacoes por tipo_busca."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(tipo_busca, 'N/A') as tipo_busca,
                   COUNT(*) as total,
                   SUM(CASE WHEN ativo = 1 THEN 1 ELSE 0 END) as ativas,
                   SUM(CASE WHEN ativo = 0 THEN 1 ELSE 0 END) as inativas
            FROM captacoes
            GROUP BY tipo_busca
            ORDER BY total DESC
        """).fetchall()
        data = [
            {
                "tipo_busca": r["tipo_busca"],
                "total": r["total"],
                "ativas": r["ativas"],
                "inativas": r["inativas"],
            }
            for r in rows
        ]
        return {"status": "success", "data": data}
    except Exception as e:
        log.error("Erro captacoes-por-tipo: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 5. Erros por tipo (error_type)
# =========================================================================

@router.get("/erros-por-tipo")
@limiter.limit("60/minute")
def erros_por_tipo(request: Request, dias: int = Query(30, ge=1, le=365)):
    """Agrupa erros do sistema por error_type nos ultimos N dias."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(error_type, 'N/A') as error_type,
                   COUNT(*) as total,
                   MAX(criado_em) as ultimo
            FROM system_errors
            WHERE criado_em >= datetime('now', 'localtime', ?)
            GROUP BY error_type
            ORDER BY total DESC
        """, (f'-{dias} days',)).fetchall()
        data = [
            {
                "error_type": r["error_type"],
                "total": r["total"],
                "ultimo": r["ultimo"],
            }
            for r in rows
        ]
        return {"status": "success", "dias": dias, "data": data}
    except Exception as e:
        log.error("Erro erros-por-tipo: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 6. Erros por funcao (function_name)
# =========================================================================

@router.get("/erros-por-funcao")
@limiter.limit("60/minute")
def erros_por_funcao(request: Request, dias: int = Query(30, ge=1, le=365)):
    """Agrupa erros do sistema por function_name nos ultimos N dias."""
    try:
        db = get_db()
        rows = db.conn.execute("""
            SELECT COALESCE(function_name, 'N/A') as function_name,
                   COUNT(*) as total,
                   MAX(criado_em) as ultimo
            FROM system_errors
            WHERE criado_em >= datetime('now', 'localtime', ?)
            GROUP BY function_name
            ORDER BY total DESC
        """, (f'-{dias} days',)).fetchall()
        data = [
            {
                "function_name": r["function_name"],
                "total": r["total"],
                "ultimo": r["ultimo"],
            }
            for r in rows
        ]
        return {"status": "success", "dias": dias, "data": data}
    except Exception as e:
        log.error("Erro erros-por-funcao: %s", e)
        return {"status": "error", "message": str(e), "data": []}


# =========================================================================
# 7. Limpar publicacoes duplicadas (manter a mais recente)
# =========================================================================

@router.post("/limpar-publicacoes-duplicadas")
@limiter.limit("30/minute")
def limpar_publicacoes_duplicadas(request: Request):
    """Remove publicacoes duplicadas por hash, mantendo a mais recente (maior id)."""
    try:
        db = get_db()
        # Contar duplicatas antes
        count_antes = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
        duplicatas = db.conn.execute("""
            SELECT COUNT(*) as c FROM publicacoes
            WHERE id NOT IN (
                SELECT MAX(id) FROM publicacoes GROUP BY hash
            )
        """).fetchone()["c"]

        if duplicatas == 0:
            return {
                "status": "success",
                "message": "Nenhuma duplicata encontrada",
                "total_antes": count_antes,
                "removidas": 0,
                "total_depois": count_antes,
            }

        db.conn.execute("""
            DELETE FROM publicacoes
            WHERE id NOT IN (
                SELECT MAX(id) FROM publicacoes GROUP BY hash
            )
        """)
        db.conn.commit()

        count_depois = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
        return {
            "status": "success",
            "message": f"{duplicatas} duplicatas removidas",
            "total_antes": count_antes,
            "removidas": duplicatas,
            "total_depois": count_depois,
        }
    except Exception as e:
        log.error("Erro limpar-publicacoes-duplicadas: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados"}


# =========================================================================
# 8. Publicacoes sem numero de processo
# =========================================================================

@router.get("/publicacoes-sem-processo")
@limiter.limit("60/minute")
def publicacoes_sem_processo(request: Request, limite: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Lista publicacoes que nao possuem numero_processo."""
    try:
        db = get_db()
        total = db.conn.execute("""
            SELECT COUNT(*) as c FROM publicacoes
            WHERE numero_processo IS NULL OR TRIM(numero_processo) = ''
        """).fetchone()["c"]

        rows = db.conn.execute("""
            SELECT id, hash, fonte, tribunal, data_publicacao,
                   classe_processual, orgao_julgador, criado_em
            FROM publicacoes
            WHERE numero_processo IS NULL OR TRIM(numero_processo) = ''
            ORDER BY criado_em DESC
            LIMIT ? OFFSET ?
        """, (limite, offset)).fetchall()
        data = [dict(r) for r in rows]
        return {
            "status": "success",
            "total": total,
            "limite": limite,
            "offset": offset,
            "data": data,
        }
    except Exception as e:
        log.error("Erro publicacoes-sem-processo: %s", e)
        return {"status": "error", "message": "Erro ao acessar banco de dados", "data": []}


# =========================================================================
# 9. Saude completa do sistema
# =========================================================================

@router.get("/saude-completa")
@limiter.limit("60/minute")
def saude_completa(request: Request):
    """Saude completa do sistema: banco, scheduler, fontes, metricas, circuits."""
    try:
        db = get_db()
        resultado = {}

        # 1. Database
        try:
            db.conn.execute("SELECT 1")
            tables = db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_counts = {}
            for t in tables:
                name = t["name"]
                c = db.conn.execute(f"SELECT COUNT(*) as c FROM [{name}]").fetchone()["c"]
                table_counts[name] = c
            db_size = db.conn.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            ).fetchone()["size"]
            resultado["database"] = {
                "status": "ok",
                "size_mb": round(db_size / 1024 / 1024, 2),
                "tables": table_counts,
            }
        except Exception as e:
            log.error("Erro database saude-completa: %s", e, exc_info=True)
            resultado["database"] = {"status": "error", "message": "Erro ao acessar banco de dados"}

        # 2. Scheduler
        try:
            from djen.api.app import _scheduler
            if _scheduler and _scheduler.running:
                jobs = [{"id": j.id, "name": j.name, "next_run": str(j.next_run_time)} for j in _scheduler.get_jobs()]
                resultado["scheduler"] = {"status": "running", "jobs": jobs}
            else:
                resultado["scheduler"] = {"status": "stopped"}
        except Exception as e:
            log.error("Erro scheduler saude-completa: %s", e, exc_info=True)
            resultado["scheduler"] = {"status": "unknown", "message": "Erro ao verificar scheduler"}

        # 3. Uptime
        try:
            from djen.api.app import _start_time
            resultado["uptime_seconds"] = int(time.time() - _start_time)
        except Exception:
            resultado["uptime_seconds"] = 0

        # 4. Metricas
        try:
            from djen.api.metrics import get_metrics
            m = get_metrics()
            resultado["metrics"] = {
                "total_requests": m.total_requests,
                "total_errors": m.total_errors,
            }
        except Exception as e:
            log.error("Erro metrics saude-completa: %s", e, exc_info=True)
            resultado["metrics"] = {"status": "error", "message": "Erro ao obter metricas"}

        # 5. Circuit Breakers
        try:
            from djen.api.circuitbreaker import get_all_circuits
            circuits = get_all_circuits()
            resultado["circuits"] = {
                name: cb.get_status() for name, cb in circuits.items()
            }
        except Exception as e:
            log.error("Erro circuits saude-completa: %s", e, exc_info=True)
            resultado["circuits"] = {"status": "error", "message": "Erro ao verificar circuit breakers"}

        # 6. Contagens rapidas
        try:
            resultado["contagens"] = {
                "publicacoes": db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"],
                "captacoes": db.conn.execute("SELECT COUNT(*) as c FROM captacoes").fetchone()["c"],
                "monitorados": db.conn.execute("SELECT COUNT(*) as c FROM monitorados WHERE ativo=1").fetchone()["c"],
                "processos_monitorados": db.conn.execute("SELECT COUNT(*) as c FROM processos_monitorados WHERE status='ativo'").fetchone()["c"],
                "erros_abertos": db.conn.execute("SELECT COUNT(*) as c FROM system_errors WHERE status='aberto'").fetchone()["c"],
            }
        except Exception as e:
            log.error("Erro contagens saude-completa: %s", e, exc_info=True)
            resultado["contagens"] = {"status": "error", "message": "Erro ao obter contagens"}

        return {"status": "success", **resultado}
    except Exception as e:
        log.error("Erro saude-completa: %s", e, exc_info=True)
        return {"status": "error", "message": "Erro interno do servidor"}
