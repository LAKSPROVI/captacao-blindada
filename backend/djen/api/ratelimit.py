"""
Rate Limiting para CAPTAÇÃO BLINDADA.

Configura limites de requisições por IP e por usuário autenticado.
"""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from typing import Optional

log = logging.getLogger("captacao.ratelimit")

# =============================================================================
# Rate Limiter Configuração
# =============================================================================

def get_client_ip(request: Request) -> str:
    """Extrai IP real considerando proxy/Nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return get_remote_address(request)


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
    
    # Geral - limite global
    "default": "60/minute",
}

# =============================================================================
# Criar Limiter
# =============================================================================

limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[RATE_LIMITS["default"]],
    storage_uri="memory://",
    strategy="fixed-window",
)


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
    import re
    match = re.match(r"(\d+)/(\w+)", limit_str)
    if match:
        count = int(match.group(1))
        unit = match.group(2)
        seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unit, 60)
        return count, seconds
    return 60, 60


log.info("Rate Limiter configurado com limites: %s", RATE_LIMITS)