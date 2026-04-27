"""
Métricas e Monitoramento para CAPTAÇÃO BLINDADA.

Sistema de coleta de métricas para monitoramento em produção.
"""
import logging
import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger("captacao.metrics")


# =============================================================================
# Métricas Simples (sem dependência externa)
# =============================================================================

class MetricsCollector:
    """
    Coletador de métricas simples.
    
    Não requer Prometheus externas - funciona standalone.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Contadores
        self._requests_total = 0
        self._requests_errors = 0
        self._captacoes_total = 0
        self._captacoes_ativas = 0
        self._publicacoes_total = 0
        self._publicacoes_hoje = 0
        
        # Histogramas (simplificado)
        self._durations: List[float] = []
        self._max_durations = 1000  # Keep last 1000
        
        # Por fonte
        self._buscas_por_fonte: Dict[str, int] = defaultdict(int)
        
        # Contadores por endpoint
        self._requests_por_endpoint: Dict[str, int] = defaultdict(int)
        
        # Erros
        self._erros_por_tipo: Dict[str, int] = defaultdict(int)
        
        # Início
        self._start_time = time.time()
        self._ultima_publicacao = None
    
    def increment_requests(self):
        """Incrementa total de requisições."""
        with self._lock:
            self._requests_total += 1
    
    def increment_errors(self, error_type: str = "generic"):
        """Incrementa contador de erros."""
        with self._lock:
            self._requests_errors += 1
            self._erros_por_tipo[error_type] += 1
    
    def record_duration(self, duration_ms: float):
        """Registra duração de requisição."""
        with self._lock:
            self._durations.append(duration_ms)
            if len(self._durations) > self._max_durations:
                self._durations.pop(0)
    
    def increment_buscas(self, fonte: str):
        """Incrementa búsquedas por fonte."""
        with self._lock:
            self._buscas_por_fonte[fonte] += 1
    
    def increment_requests_endpoint(self, endpoint: str):
        """Incrementa requisições por endpoint."""
        with self._lock:
            self._requests_por_endpoint[endpoint] += 1
    
    def increment_captacoes(self):
        """Incrementa total de captações."""
        with self._lock:
            self._captacoes_total += 1
    
    def set_captacoes_ativas(self, count: int):
        """Define total de captações ativas."""
        with self._lock:
            self._captacoes_ativas = count
    
    def increment_publicacoes(self):
        """Incrementa publicações encontradas."""
        with self._lock:
            self._publicacoes_total += 1
            self._publicacoes_hoje += 1
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas."""
        with self._lock:
            uptime = time.time() - self._start_time
            
            # Calcular duração média
            durations = self._durations
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Percentis (simplificado)
            sorted_dur = sorted(durations)
            p50 = sorted_dur[len(sorted_dur)//2] if sorted_dur else 0
            p95 = sorted_dur[min(int(len(sorted_dur)*0.95), len(sorted_dur)-1)] if sorted_dur else 0
            p99 = sorted_dur[min(int(len(sorted_dur)*0.99), len(sorted_dur)-1)] if sorted_dur else 0
            
            return {
                "requests_total": self._requests_total,
                "requests_per_minute": round(self._requests_total / (uptime / 60), 2) if uptime > 0 else 0,
                "request_duration_avg_ms": round(avg_duration, 2),
                "request_duration_p50_ms": round(p50, 2),
                "request_duration_p95_ms": round(p95, 2),
                "request_duration_p99_ms": round(p99, 2),
                "errors_total": self._requests_errors,
                "error_rate": round(self._requests_errors / self._requests_total, 4) if self._requests_total > 0 else 0,
                "buscas_por_fonte": dict(self._buscas_por_fonte),
                "requests_por_endpoint": dict(self._requests_por_endpoint),
                "erros_por_tipo": dict(self._erros_por_tipo),
                "captacoes_total": self._captacoes_total,
                "captacoes_ativas": self._captacoes_ativas,
                "publicacoes_total": self._publicacoes_total,
                "publicacoes_hoje": self._publicacoes_hoje,
                "uptime_seconds": int(uptime),
            }


# =============================================================================
# Prometheus Format (Compatible)
# =============================================================================

def format_prometheus(metrics: MetricsCollector) -> str:
    """Formata métricas em formato Prometheus válido."""
    lines = []
    stats = metrics.get_stats()
    
    lines.append("# HELP api_requests_total Total de requisicoes recebidas")
    lines.append("# TYPE api_requests_total counter")
    lines.append(f'api_requests_total {stats["requests_total"]}')
    
    lines.append("# HELP api_requests_errors_total Total de erros")
    lines.append("# TYPE api_requests_errors_total counter")
    lines.append(f'api_requests_errors_total {stats["errors_total"]}')
    
    lines.append("# HELP api_request_duration_seconds Duracao das requisicoes")
    lines.append("# TYPE api_request_duration_seconds summary")
    lines.append(f'api_request_duration_seconds_sum {stats["request_duration_avg_ms"] / 1000}')
    lines.append(f'api_request_duration_seconds_count {stats["requests_total"]}')
    
    lines.append("# HELP captacao_total Total de captacoes criadas")
    lines.append("# TYPE captacao_total gauge")
    lines.append(f'captacao_total {stats["captacoes_total"]}')
    lines.append(f'captacao_ativas {stats["captacoes_ativas"]}')
    
    lines.append("# HELP publicacao_total Total de publicacoes")
    lines.append("# TYPE publicacao_total counter")
    lines.append(f'publicacao_total {stats["publicacoes_total"]}')
    lines.append(f'publicacao_hoje {stats["publicacoes_hoje"]}')
    
    for fonte, count in stats["buscas_por_fonte"].items():
        lines.append(f'busca_fonte{{fonte="{fonte}"}} {count}')
    
    lines.append("# HELP process_uptime_seconds Tempo de atividade do processo")
    lines.append("# TYPE process_uptime_seconds gauge")
    lines.append(f'process_uptime_seconds {stats["uptime_seconds"]}')
    
    return "\n".join(lines)


# =============================================================================
# Instância Global
# =============================================================================

_metrics: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Retorna coletador global."""
    global _metrics
    with _metrics_lock:
        if _metrics is None:
            _metrics = MetricsCollector()
    return _metrics


# =============================================================================
# Decorators Prontos
# =============================================================================

def track_request(endpoint: str):
    """Decorator para tracking de requisições (suporta sync e async)."""
    import functools
    import asyncio
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                get_metrics().increment_requests()
                get_metrics().increment_requests_endpoint(endpoint)
                return result
            except Exception as e:
                get_metrics().increment_errors(type(e).__name__)
                raise
            finally:
                duration = (time.time() - start) * 1000
                get_metrics().record_duration(duration)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                get_metrics().increment_requests()
                get_metrics().increment_requests_endpoint(endpoint)
                return result
            except Exception as e:
                get_metrics().increment_errors(type(e).__name__)
                raise
            finally:
                duration = (time.time() - start) * 1000
                get_metrics().record_duration(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


log.debug("Metrics collector configurado")