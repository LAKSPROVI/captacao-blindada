"""
Webhooks para CAPTAÇÃO BLINDADA.

Sistema de notificações automáticas quando eventos acontecem.
"""
import logging
import time
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

log = logging.getLogger("captacao.webhook")


# =============================================================================
# Configuração de Webhook
# =============================================================================

@dataclass
class WebhookConfig:
    """Configuração de um webhook."""
    id: str
    url: str
    events: List[str]
    enabled: bool = True
    secret_token: Optional[str] = None
    retry_count: int = 3
    timeout: int = 10


# =============================================================================
# Tipos de Eventos
# =============================================================================

class WebhookEvent:
    """Tipos de eventos suportados."""
    NEW_PUBLICATION = "new_publication"
    CAPTACAO_COMPLETED = "captacao_completed"
    PROCESS_UPDATE = "process_update"
    NEW_RESULT = "new_result"


# =============================================================================
# Webhook Manager
# =============================================================================

class WebhookManager:
    """
    Gerenciador de webhooks.
    
    Envia notificações para URLs configuradas quando eventos acontecem.
    """
    
    def __init__(self):
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._lock = threading.Lock()
        self._session: Optional[requests.Session] = None
    
    def _get_session(self) -> requests.Session:
        """Retorna sessão HTTP com retry."""
        if self._session is None:
            self._session = requests.Session()
            retry = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        return self._session
    
    def add_webhook(
        self,
        webhook_id: str,
        url: str,
        events: List[str],
        secret_token: Optional[str] = None,
    ) -> bool:
        """Adiciona um webhook."""
        with self._lock:
            # Validar URL
            try:
                requests.URL(url)
            except Exception:
                log.error(f"URL inválida: {url}")
                return False
            
            self._webhooks[webhook_id] = WebhookConfig(
                id=webhook_id,
                url=url,
                events=events,
                secret_token=secret_token,
            )
            log.info(f"Webhook adicionado: {webhook_id} -> {url}")
            return True
    
    def remove_webhook(self, webhook_id: str) -> bool:
        """Remove um webhook."""
        with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                log.info(f"Webhook removido: {webhook_id}")
                return True
            return False
    
    def get_webhooks(self) -> List[Dict]:
        """Lista webhooks configurados (sem URL sensível)."""
        with self._lock:
            return [
                {
                    "id": w.id,
                    "url": w.url[:20] + "..." if len(w.url) > 20 else w.url,
                    "events": w.events,
                    "enabled": w.enabled,
                }
                for w in self._webhooks.values()
            ]
    
    def trigger(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Dispara webhook para todos os listeners do evento.
        
        Returns dict com resultados.
        """
        results = {
            "event": event,
            "total": 0,
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        with self._lock:
            webhook_list = [
                w for w in self._webhooks.values()
                if w.enabled and event in w.events
            ]
        
        results["total"] = len(webhook_list)
        
        payload = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        
        for webhook in webhook_list:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event,
                    "X-Webhook-Id": webhook.id,
                }
                
                if webhook.secret_token:
                    headers["Authorization"] = f"Bearer {webhook.secret_token}"
                
                response = self._session.post(
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=webhook.timeout,
                )
                
                if response.status_code < 400:
                    results["sent"] += 1
                    detail = {"id": webhook.id, "status": "sent", "code": response.status_code}
                else:
                    results["failed"] += 1
                    detail = {"id": webhook.id, "status": "error", "code": response.status_code, "message": response.text[:100]}
                
            except Exception as e:
                results["failed"] += 1
                detail = {"id": webhook.id, "status": "error", "message": str(e)[:100]}
                log.error(f"Webhook erro {webhook.id}: {e}")
            
            results["details"].append(detail)
        
        return results


# =============================================================================
# Instância Global
# =============================================================================

_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Retorna instância global do manager."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


def trigger_webhook(
    event: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Função helper para disparar webhook."""
    return get_webhook_manager().trigger(event, data)


log.info("Webhook Manager configurado")