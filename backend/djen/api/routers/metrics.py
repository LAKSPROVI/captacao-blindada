"""
Router de Métricas - CAPTAÇÃO BLINDADA.

Endpoints para monitoramento e métricas.
"""
import logging

from fastapi import APIRouter, Response

from djen.api.metrics import get_metrics, format_prometheus

log = logging.getLogger("captacao.metrics")
router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", summary="Métricas em JSON")
def get_metrics_json():
    """
    Retorna métricas em formato JSON.
    
    Inclui contadores, histogramas e estatísticas.
    """
    metrics = get_metrics()
    stats = metrics.get_stats()
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "metrics": stats,
    }


@router.get("/prometheus", summary="Métricas em formato Prometheus")
def get_metrics_prometheus():
    """
    Retorna métricas em formato Prometheus.
    
    Use para integração com Grafana/Prometheus.
    """
    metrics = get_metrics()
    output = format_prometheus(metrics)
    
    return Response(
        content=output,
        media_type="text/plain",
    )


@router.get("/health", summary="Health check com métricas")
def get_health_with_metrics():
    """
    Health check com métricas resumidas.
    """
    from djen.api.database import get_database
    
    metrics = get_metrics()
    stats = metrics.get_stats()
    
    # Check database
    db_status = "ok"
    try:
        db = get_database()
        db.conn.execute("SELECT 1")
    except Exception:
        db_status = "error"
    
    # Status geral
    error_rate = stats.get("error_rate", 0)
    if error_rate > 0.1:
        status = "error"
    elif error_rate > 0.01:
        status = "degraded"
    else:
        status = "ok"
    
    return {
        "status": status,
        "database": db_status,
        "uptime_seconds": stats.get("uptime_seconds", 0),
        "requests_total": stats.get("requests_total", 0),
        "error_rate": error_rate,
    }


@router.post("/reset", summary="Resetar métricas")
def reset_metrics():
    """Reseta todas as métricas (use com cautela)."""
    global _metrics
    _metrics = None
    get_metrics()  # Recria
    
    return {
        "status": "success",
        "message": "Métricas foram resetadas",
    }


from datetime import datetime