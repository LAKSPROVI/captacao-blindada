"""
Cache Avançado para CAPTAÇÃO BLINDADA.

Cache em memória ou Redis (opcional).
"""
import logging
import time
import threading
from typing import Any, Optional, Dict
from dataclasses import dataclass
import json

log = logging.getLogger("captacao.cache")


# =============================================================================
# Cache Item
# =============================================================================

@dataclass
class CacheItem:
    """Item do cache."""
    key: str
    value: Any
    expires_at: float  # timestamp
    created_at: float
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


# =============================================================================
# Cache Manager
# =============================================================================

class CacheManager:
    """
    Gerenciador de cache com fallback.
    
    Suporta Redis (opcional) ou memória local.
    """
    
    def __init__(self):
        self._cache: Dict[str, CacheItem] = {}
        self._lock = threading.RLock()
        
        # Config
        self._default_ttl = 300  # 5 minutos
        self._max_items = 10000
        
        # Redis (opcional)
        self._redis = None
        self._use_redis = False
        
        # Stats
        self._hits = 0
        self._misses = 0
    
    def configure_redis(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
    ) -> bool:
        """Configure Redis (opcional)."""
        try:
            import redis
            self._redis = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=True,
            )
            # Teste conexão
            self._redis.ping()
            self._use_redis = True
            log.info(f"[Cache] Conectado ao Redis {host}:{port}")
            return True
        except ImportError:
            log.warning("[Cache] redis package não instalado, usando memória")
            return False
        except Exception as e:
            log.warning(f"[Cache] Erro ao conectar no Redis: {e}, usando memória")
            return False
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Define valor no cache."""
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        
        item = CacheItem(
            key=key,
            value=value,
            expires_at=expires_at,
            created_at=time.time(),
        )
        
        with self._lock:
            # Redis
            if self._use_redis and self._redis:
                try:
                    self._redis.setex(
                        f"captacao:{key}",
                        ttl,
                        json.dumps(value),
                    )
                    return True
                except Exception:
                    pass
            
            # Memória
            self._cache[key] = item
            
            # Limpa cache se muito grande
            if len(self._cache) > self._max_items:
                self._cleanup()
            
            return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get valor do cache."""
        with self._lock:
            # Redis
            if self._use_redis and self._redis:
                try:
                    value = self._redis.get(f"captacao:{key}")
                    if value:
                        self._hits += 1
                        return json.loads(value)
                except Exception:
                    pass
            
            # Memória
            item = self._cache.get(key)
            if item:
                if item.is_expired():
                    del self._cache[key]
                    self._misses += 1
                else:
                    self._hits += 1
                    return item.value
            
            self._misses += 1
            return default
    
    def delete(self, key: str) -> bool:
        """Deleta do cache."""
        with self._lock:
            # Redis
            if self._use_redis and self._redis:
                try:
                    self._redis.delete(f"captacao:{key}")
                except Exception:
                    pass
            
            # Memória
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> bool:
        """Limpa todo cache."""
        with self._lock:
            # Redis
            if self._use_redis and self._redis:
                try:
                    cursor = 0
                    while True:
                        cursor, keys = self._redis.scan(cursor, match="captacao:*", count=100)
                        if keys:
                            self._redis.delete(*keys)
                        if cursor == 0:
                            break
                except Exception:
                    pass
            
            # Memória
            self._cache.clear()
            return True
    
    def _cleanup(self):
        """Remove itens expirados."""
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for k in expired:
            del self._cache[k]
        
        # Se ainda grande, remove mais antigos
        if len(self._cache) > self._max_items:
            items = sorted(self._cache.items(), key=lambda x: x[1].created_at)
            for k, _ in items[:len(self._cache) - self._max_items + 100]:
                del self._cache[k]
    
    def stats(self) -> Dict:
        """Retorna estatísticas."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "backend": "redis" if self._use_redis else "memory",
                "items": len(self._cache),
            }


# =============================================================================
# Instância Global
# =============================================================================

_cache: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache() -> CacheManager:
    """Retorna gerenciador de cache."""
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = CacheManager()
    return _cache


log.debug("Cache manager loaded (supports Redis optionally)")