"""
Rate Limiting para CAPTAÇÃO BLINDADA.

Configura limites de requisições por IP e por usuário autenticado.
Suporta Redis como backend para ambientes multi-worker.
"""
import logging
import os
import re
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from typing import Optional

log = logging.getLogger("captacao.ratelimit")

# =============================================================================
# Rate Limiter Configuração
# =============================================================================

# IPs de proxies confiáveis (configurar via env)
TRUSTED_PROXIES = set(
    p.strip() for p in os.environ.get("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if p.strip()
)

def get_client_ip(request: Request) -> str:
    """Extrai IP real, confiando em X-Forwarded-For apenas de proxies conhecidos."""
    client_host = get_remote_address(request)
    # Só confiar em headers de proxy se o request vem de um proxy confiável
    if client_host in TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
    return client_host


def get_user_identifier(request: Request) -> str:
    """Usa IP ou username se autenticado."""
    # Tenta obter IP primeiro
    client_ip = get_client_ip(request)
    
    # Se tiver usuário logado, usa ID como identificador
    try:
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            return f"user:{user.id}"
    except Exception:
        pass
    
    return f"ip:{client_ip}"


# =============================================================================
# Limites por Endpoint
# =============================================================================

RATE_LIMITS = {
    # Autenticação - mais restrito
    "auth_login": "5/minute",
    "auth_register": "10/minute",
    
    # Buscas em fontes externas - médio
    "busca_datajud": "30/minute",
    "busca_djen": "30/minute",
    "busca_unificada": "30/minute",
    
    # Captação - médio
    "captacao": "10/minute",
    "captacao_executar": "5/minute",
    
    # Processo - médio
    "processo": "20/minute",
    
    # Monitor - médio
    "monitor": "20/minute",
    
    # Data modification (POST/PUT/DELETE)
    "data_modify": "30/minute",
    
    # Data export
    "data_export": "5/minute",
    
    # Search/query
    "search": "60/minute",
    
    # Admin operations (backup, purge, settings)
    "admin": "10/minute",
    
    # AI/LLM endpoints (expensive)
    "ai": "10/minute",
    
    # WebSocket connections
    "websocket": "5/minute",
    
    # Geral - limite global
    "default": "60/minute",
}

# =============================================================================
# Storage backend: Redis when available, fallback to memory
# =============================================================================

def _get_storage_uri() -> str:
    """Resolve storage URI: use Redis if REDIS_URL is set, otherwise memory."""
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        log.info("Rate Limiter usando Redis: %s", redis_url.split("@")[-1])
        return redis_url
    log.info("Rate Limiter usando storage em memória (set REDIS_URL for multi-worker)")
    return "memory://"


_storage_uri = _get_storage_uri()

# =============================================================================
# Criar Limiter
# =============================================================================

limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[RATE_LIMITS["default"]],
    storage_uri=_storage_uri,
    strategy="fixed-window",
)


def get_limiter() -> Limiter:
    """Retorna a instância singleton do limiter."""
    return limiter


# =============================================================================
# Decorators Prontos
# =============================================================================

# Limite para login
limit_auth_login = limiter.limit(RATE_LIMITS["auth_login"])

# Limite para buscas
limit_busca = limiter.limit(RATE_LIMITS["busca_datajud"])

# Limite para captacao
limit_captacao = limiter.limit(RATE_LIMITS["captacao"])

# Limite para processo
limit_processo = limiter.limit(RATE_LIMITS["processo"])

# Limite para monitor
limit_monitor = limiter.limit(RATE_LIMITS["monitor"])

# Limite para modificação de dados
limit_data_modify = limiter.limit(RATE_LIMITS["data_modify"])

# Limite para exportação
limit_data_export = limiter.limit(RATE_LIMITS["data_export"])

# Limite para busca/query
limit_search = limiter.limit(RATE_LIMITS["search"])

# Limite para admin
limit_admin = limiter.limit(RATE_LIMITS["admin"])

# Limite para IA
limit_ai = limiter.limit(RATE_LIMITS["ai"])

# Limite para WebSocket
limit_websocket = limiter.limit(RATE_LIMITS["websocket"])


# =============================================================================
# Funções Auxiliares
# =============================================================================

def get_rate_limit_headers(limit: int, remaining: int, reset: int) -> dict:
    """Retorna headers padrão de rate limiting."""
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset),
    }


def parse_limit(limit_str: str) -> tuple:
    """Parse '30/minute' -> (30, 60)"""
    match = re.match(r"(\d+)/(\w+)", limit_str)
    if match:
        count = int(match.group(1))
        unit = match.group(2)
        seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unit, 60)
        return count, seconds
    return 60, 60


log.debug("Rate Limiter configurado com limites: %s (storage: %s)", RATE_LIMITS, _storage_uri)