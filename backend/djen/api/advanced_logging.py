"""
Logging Avançado para CAPTAÇÃO BLINDADA.

Logging estruturado para debugging e auditoria.
"""
import logging
import json
import sys
import threading
from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StructuredLog:
    """Log estruturado."""
    timestamp: str
    level: str
    logger: str
    message: str
    function: Optional[str] = None
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    request_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AdvancedLogger:
    """Logger estruturado avançado."""
    
    def __init__(self, name: str = "captacao"):
        self.logger = logging.getLogger(name)
        self._logs: list = []
        self._max_logs = 10000
        self._lock = threading.Lock()
        
        # Configuração
        self._log_to_console = True
        self._log_to_file = False
        self._log_to_json = True
    
    def _format_message(
        self,
        level: str,
        message: str,
        function: Optional[str] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        request_id: Optional[str] = None,
        extra: Optional[Dict] = None,
    ) -> str:
        """Formata mensagem estruturada."""
        log_entry = StructuredLog(
            timestamp=datetime.now().isoformat(),
            level=level,
            logger=self.logger.name,
            message=message,
            function=function,
            user_id=user_id,
            tenant_id=tenant_id,
            request_id=request_id,
            extra=extra or {},
        )
        
        if self._log_to_json:
            return json.dumps(log_entry.to_dict())
        
        # Plain text
        parts = [
            f"[{log_entry.timestamp}]",
            f"[{level.upper()}]",
            f"[{self.logger.name}]",
            message,
        ]
        if function:
            parts.insert(2, f"[{function}]")
        return " ".join(parts)
    
    def debug(
        self,
        message: str,
        function: Optional[str] = None,
        **kwargs
    ):
        """Log debug."""
        msg = self._format_message("debug", message, function, **kwargs)
        self.logger.debug(msg)
        self._append_log(msg)
    
    def info(
        self,
        message: str,
        function: Optional[str] = None,
        **kwargs
    ):
        """Log info."""
        msg = self._format_message("info", message, function, **kwargs)
        self.logger.info(msg)
        self._append_log(msg)
    
    def warning(
        self,
        message: str,
        function: Optional[str] = None,
        **kwargs
    ):
        """Log warning."""
        msg = self._format_message("warning", message, function, **kwargs)
        self.logger.warning(msg)
        self._append_log(msg)
    
    def error(
        self,
        message: str,
        function: Optional[str] = None,
        **kwargs
    ):
        """Log error."""
        msg = self._format_message("error", message, function, **kwargs)
        self.logger.error(msg)
        self._append_log(msg)
    
    def critical(
        self,
        message: str,
        function: Optional[str] = None,
        **kwargs
    ):
        """Log critical."""
        msg = self._format_message("critical", message, function, **kwargs)
        self.logger.critical(msg)
        self._append_log(msg)
    
    def audit(
        self,
        action: str,
        user_id: int,
        tenant_id: Optional[int],
        details: Dict,
    ):
        """Log de auditoria."""
        msg = self._format_message(
            "info",
            f"AUDIT: {action}",
            function=action,
            user_id=user_id,
            tenant_id=tenant_id,
            extra=details,
        )
        self.logger.info(msg)
        self._append_log(msg)
    
    def _append_log(self, message: str):
        """Adiciona log à lista."""
        with self._lock:
            self._logs.append(message)
            if len(self._logs) > self._max_logs:
                self._logs.pop(0)
    
    def get_recent(self, limit: int = 100, level: Optional[str] = None) -> List[str]:
        """Retorna logs recentes."""
        with self._lock:
            logs = self._logs[-limit:]
            if level:
                logs = [l for l in logs if f"[{level.upper()}]" in l]
            return logs
    
    def search(
        self,
        query: str,
        limit: int = 100,
    ) -> List[str]:
        """Busca em logs."""
        with self._lock:
            return [l for l in self._logs if query.lower() in l.lower()][-limit:]


# =============================================================================
# Instância Global
# =============================================================================

_loggers: Dict[str, AdvancedLogger] = {}


def get_logger(name: str = "captacao") -> AdvancedLogger:
    """Retorna logger."""
    if name not in _loggers:
        _loggers[name] = AdvancedLogger(name)
    return _loggers[name]


def configure_logging(
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str = "/var/log/captacao/app.log",
):
    """Configura logging global."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    if log_to_file:
        handler = logging.FileHandler(log_file_path)
        logging.getLogger("captacao").addHandler(handler)


# Configurar padrão
configure_logging()