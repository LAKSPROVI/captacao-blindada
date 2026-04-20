"""
Captacao Peticao Blindada - Router Health.
Health check unificado de todas as fontes.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter

from djen.api.schemas import HealthResponse, HealthSourceResponse

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
        return HealthSourceResponse(
            source=name, status="error", message=str(e)
        )


@router.get("/api/health", response_model=HealthResponse, summary="Health check completo")
def health_check_completo():
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
                fontes_results.append(HealthSourceResponse(
                    source=name, status="error", message=str(e)
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
def health_circuits():
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
def reset_circuits():
    """Reseta todos os Circuit Breakers (use com cautela)."""
    from djen.api.circuitbreaker import reset_all_circuits
    
    reset_all_circuits()
    return {"status": "success", "message": "Todos os circuits foram resetados"}
