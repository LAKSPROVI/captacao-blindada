"""
Captacao Peticao Blindada - Router Health.
Health check unificado de todas as fontes.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import Request, APIRouter

from djen.api.schemas import HealthResponse, HealthSourceResponse
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.health")
router = APIRouter(tags=["Health"])


def _check_source(source_cls, name: str) -> HealthSourceResponse:
    """Executa health check de uma fonte."""
    try:
        t0 = time.time()
        source = source_cls()
        result = source.health_check()
        latency = int((time.time() - t0) * 1000)
        return HealthSourceResponse(
            source=name,
            status=result.get("status", "error"),
            message=result.get("message"),
            latency_ms=latency,
            proxy_used=result.get("proxy_used"),
        )
    except Exception as e:
        log.error("Erro health check fonte %s: %s", name, e, exc_info=True)
        return HealthSourceResponse(
            source=name, status="error", message="Erro ao verificar fonte"
        )


@router.get("/api/health", response_model=HealthResponse, summary="Health check completo")
@limiter.limit("60/minute")
def health_check_completo(request: Request):
    """
    Verifica o status de todas as fontes em paralelo.
    Retorna status individual de cada fonte + banco + scheduler.
    """
    from djen.sources.datajud import DatajudSource
    from djen.sources.djen_source import DjenSource

    fontes_config = [
        (DatajudSource, "datajud"),
        (DjenSource, "djen_api"),
    ]

    fontes_results = []

    # Executar health checks em paralelo
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_check_source, cls, name): name
            for cls, name in fontes_config
        }
        for future in as_completed(futures, timeout=60):
            try:
                fontes_results.append(future.result())
            except Exception as e:
                name = futures[future]
                log.error("Erro health check fonte %s: %s", name, e, exc_info=True)
                fontes_results.append(HealthSourceResponse(
                    source=name, status="error", message="Erro ao verificar fonte"
                ))

    # Status geral
    all_ok = all(f.status == "ok" for f in fontes_results)
    any_ok = any(f.status == "ok" for f in fontes_results)

    # Database check
    db_status = "ok"
    try:
        from djen.api.database import get_database
        db = get_database()
        db.conn.execute("SELECT 1")
    except Exception:
        db_status = "error"

    # Scheduler check
    sched_status = "ok"
    try:
        from djen.api.app import _scheduler
        if _scheduler and _scheduler.running:
            sched_status = "running"
        else:
            sched_status = "stopped"
    except Exception:
        sched_status = "unknown"

    # Uptime
    try:
        from djen.api.app import _start_time
        uptime = int(time.time() - _start_time)
    except Exception:
        uptime = 0

    return HealthResponse(
        status="ok" if all_ok else ("degraded" if any_ok else "error"),
        version="1.0.0",
        uptime_seconds=uptime,
        fontes=fontes_results,
        database=db_status,
        scheduler=sched_status,
    )


@router.get("/api/health/circuits", summary="Status dos Circuit Breakers")
@limiter.limit("60/minute")
def health_circuits(request: Request):
    """
    Retorna o status de todos os Circuit Breakers.
    """
    from djen.api.circuitbreaker import get_all_circuits, reset_all_circuits
    
    circuits = get_all_circuits()
    status = {
        name: cb.get_status()
        for name, cb in circuits.items()
    }
    
    return {
        "status": "success",
        "total": len(status),
        "circuits": status,
    }


@router.post("/api/health/circuits/reset", summary="Resetar todos os Circuit Breakers")
@limiter.limit("5/minute")
def reset_circuits(request: Request):
    """Reseta todos os Circuit Breakers (use com cautela)."""
    from djen.api.circuitbreaker import reset_all_circuits
    
    reset_all_circuits()
    return {"status": "success", "message": "Todos os circuits foram resetados"}


@router.get("/api/health/database", summary="Saúde detalhada do banco")
@limiter.limit("60/minute")
def health_database(request: Request):
    """Retorna informações detalhadas do banco de dados."""
    from djen.api.database import get_database
    db = get_database()
    
    try:
        tables = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        table_stats = {}
        for t in tables:
            name = t["name"]
            count = db.conn.execute(f"SELECT COUNT(*) as c FROM [{name}]").fetchone()["c"]
            table_stats[name] = count
        
        db_size = db.conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()").fetchone()["size"]
        wal_mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
        
        return {
            "status": "ok",
            "size_bytes": db_size,
            "size_mb": round(db_size / 1024 / 1024, 2),
            "journal_mode": wal_mode,
            "tables": table_stats,
            "total_tables": len(table_stats),
        }
    except Exception as e:
        log.error("Erro health database: %s", e, exc_info=True)
        return {"status": "error", "message": "Erro ao acessar banco de dados"}


@router.get("/api/health/system", summary="Informações do sistema")
@limiter.limit("60/minute")
def health_system(request: Request):
    """Retorna informações do sistema operacional e runtime."""
    import platform
    import sys
    import os
    from datetime import datetime
    
    return {
        "status": "ok",
        "python_version": sys.version,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "timezone": os.environ.get("TZ", "UTC"),
        "datetime": datetime.now().isoformat(),
        "pid": os.getpid(),
        "cpu_count": os.cpu_count(),
    }
