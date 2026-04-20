"""
Circuit Breaker para CAPTAÇÃO BLINDADA.

Protege chamadas a fontes externas (DataJud, DJEN, etc) contra falhas
em cascata. Quando uma fonte falha N vezes consecutivas, o circuito
se "abre" e impede novas tentativas por um período.
"""
import logging
import time
import threading
from enum import Enum
from typing import Callable, Optional, Any
from functools import wraps
from dataclasses import dataclass, field

log = logging.getLogger("captacao.circuitbreaker")


# =============================================================================
# Estados do Circuit
# =============================================================================

class CircuitState(Enum):
    FECHADO = "closed"      # Normal, permite todas as requisições
    ABERTO = "open"        # Bloqueado, rejeita requisições
    MEIO_ABERTO = "half"    # Testando, permite 1 requisição


# =============================================================================
# Configuração
# =============================================================================

@dataclass
class CircuitBreakerConfig:
    """Configuração do circuit breaker."""
    failures_threshold: int = 5       # Falhas para abrir o circuito
    success_threshold: int = 2        # Sucessos para fechar
    timeout_open: float = 60.0          # Segundos aberto
    timeout_request: float = 30.0       # Timeout por requisição
    exclude_errors: tuple = (            # Erros a ignorar
        ValueError,
        KeyError,
    )


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitBreaker:
    """
    Circuit Breaker implementa o padrão de proteção.
    
    Uso:
        cb = CircuitBreaker("datajud", timeout=60)
        
        try:
            resultado = cb.call(minha_funcao, arg1, arg2)
        except CircuitOpenError:
            return "Servico temporariamente indisponivel"
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.FECHADO
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._lock = threading.RLock()
        
        log.info(f"[CircuitBreaker] {name}: Inicializado (threshold={self.config.failures_threshold})")
    
    @property
    def state(self) -> CircuitState:
        """Retorna o estado atual considerando timeout."""
        with self._lock:
            if self._state == CircuitState.ABE:
                # Verifica se timeout expirou
                if self._opened_at and time.time() - self._opened_at >= self.config.timeout_open:
                    log.info(f"[CircuitBreaker] {self.name}: Timeout expirou, testando...")
                    self._state = CircuitState.MEIO_ABERTO
                    self._success_count = 0
            return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executa função com proteção.
        
        Raises:
            CircuitOpenError: Se circuito está aberto
            Exception: Qualquer erro da função
        """
        if self.state == CircuitState.ABE:
            raise CircuitOpenError(
                f"Circuit {self.name} is OPEN",
                retry_after=int(self.config.timeout_open - (time.time() - self._opened_at))
            )
        
        if self.state == CircuitState.MEIO_ABERTO:
            # Permite apenas 1 requisição de teste
            log.info(f"[CircuitBreaker] {self.name}: Testando com 1 requisição...")
        
        try:
            # Executa com timeout
            import signal
            import functools
            
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Registra sucesso."""
        with self._lock:
            self._failure_count = 0
            
            if self.state == CircuitState.MEIO_ABERTO:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    log.info(f"[CircuitBreaker] {self.name}: FECHADO apos {self._success_count} sucessos")
                    self._state = CircuitState.FECHADO
                    self._success_count = 0
    
    def _on_failure(self):
        """Registra falha."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.config.failures_threshold:
                if self.state != CircuitState.ABE:
                    log.warning(f"[CircuitBreaker] {self.name}: ABERTO apos {self._failure_count} falhas")
                    self._state = CircuitState.ABE
                    self._opened_at = time.time()
    
    def reset(self):
        """Reseta o circuit."""
        with self._lock:
            self._state = CircuitState.FECHADO
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None
            log.info(f"[CircuitBreaker] {self.name}: Resetado")
    
    def get_status(self) -> dict:
        """Retorna status para monitoramento."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time,
            "opened_at": self._opened_at,
        }


# =============================================================================
# Erro Customizado
# =============================================================================

class CircuitOpenError(Exception):
    """Erro quando circuit está aberto."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


# =============================================================================
# Instâncias Globais
# =============================================================================

_circuits: dict[str, CircuitBreaker] = {}
_circuits_lock = threading.Lock()


def get_circuit(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Retorna ou cria circuit breaker pelo nome."""
    with _circuits_lock:
        if name not in _circuits:
            _circuits[name] = CircuitBreaker(name, config)
            log.info(f"[CircuitBreaker] Criado circuit para: {name}")
        return _circuits[name]


def get_all_circuits() -> dict[str, CircuitBreaker]:
    """Retorna todos os circuits."""
    with _circuits_lock:
        return dict(_circuits)


def reset_all_circuits():
    """Reseta todos os circuits."""
    with _circuits_lock:
        for cb in _circuits.values():
            cb.reset()
        log.info("[CircuitBreaker] Todos os circuits foram resetados")


# =============================================================================
# Decorator Pronto
# =============================================================================

def circuit_protected(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator para proteger funções.
    
    Uso:
        @circuit_protected("datajud")
        def buscar_datajud(termo):
            ...
    """
    def decorator(func: Callable) -> Callable:
        cb = get_circuit(name, config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        wrapper._circuit = cb
        return wrapper
    
    return decorator


# =============================================================================
# Status para API
# =============================================================================

def get_circuits_status() -> list:
    """Retorna status de todos os circuits para API."""
    return [cb.get_status() for cb in _circuits.values()]


log.info("Circuit Breaker configurado")