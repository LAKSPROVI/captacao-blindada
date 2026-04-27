"""
Router de Webhooks - CAPTAÇÃO BLINDADA.

Endpoints para configurar e gerenciar webhooks.
"""
import logging
from typing import Optional, List

from fastapi import Request, APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from pydantic import Field
from djen.api.auth import get_current_user, UserInDB

from djen.api.ratelimit import limiter
from djen.api.webhook import (
    get_webhook_manager,
    WebhookEvent,
    trigger_webhook,
)

log = logging.getLogger("captacao.webhook")
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


# =============================================================================
# Request Models
# =============================================================================

class CreateWebhookRequest(BaseModel):
    """Request para criar webhook."""
    url: str = Field(..., description="URL do webhook", example="https://seu-servidor.com/webhook")
    events: List[str] = Field(..., description="Eventos a assinar", example=["new_publication", "captacao_completed"])
    secret_token: Optional[str] = Field(None, description="Token para autenticação (opcional)")


class TriggerTestRequest(BaseModel):
    """Request para testar webhook."""
    url: str = Field(..., description="URL para testar")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", summary="Listar webhooks")
@limiter.limit("60/minute")
def listar_webhooks(request: Request):
    """Lista todos os webhooks configurados."""
    manager = get_webhook_manager()
    webhooks = manager.get_webhooks()
    
    return {
        "status": "success",
        "total": len(webhooks),
        "webhooks": webhooks,
    }


@router.post("", summary="Criar webhook")
@limiter.limit("30/minute")
def criar_webhook(request: CreateWebhookRequest, webhook_id: str = Body(..., description="ID único")):
    """Cria um novo webhook."""
    manager = get_webhook_manager()
    
    # Validar eventos
    eventos_validos = [WebhookEvent.NEW_PUBLICATION, WebhookEvent.CAPTACAO_COMPLETED, WebhookEvent.PROCESS_UPDATE, WebhookEvent.NEW_RESULT]
    for event in request.events:
        if event not in eventos_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Evento inválido: {event}. Use: {eventos_validos}"
            )
    
    # Adicionar
    success = manager.add_webhook(
        webhook_id=webhook_id,
        url=request.url,
        events=request.events,
        secret_token=request.secret_token,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="URL inválida")
    
    return {
        "status": "success",
        "message": f"Webhook {webhook_id} criado",
        "url": request.url,
        "events": request.events,
    }


@router.delete("/{webhook_id}", summary="Remover webhook")
@limiter.limit("30/minute")
def remover_webhook(request: Request, webhook_id: str):
    """Remove um webhook."""
    manager = get_webhook_manager()
    success = manager.remove_webhook(webhook_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    
    return {
        "status": "success",
        "message": f"Webhook {webhook_id} removido",
    }


@router.post("/test", summary="Testar webhook")
@limiter.limit("5/minute")
def testar_webhook(request: TriggerTestRequest):
    """Envia um teste para URL especificada."""
    from djen.api.webhook import WebhookManager
    
    # Criar manager temporário para testar
    temp_manager = WebhookManager()
    temp_manager._webhooks["test"] = temp_manager.WebhookConfig(
        id="test",
        url=request.url,
        events=["new_publication"],
        secret_token=None,
    )
    
    result = temp_manager.trigger("new_publication", {
        "test": True,
        "message": "Teste de webhook",
        "source": "CAPTACAO_BLINDADA",
    })
    
    return result


@router.post("/trigger/{event}", summary="Disparar webhook manualmente")
@limiter.limit("30/minute")
def Disparar(request: Request, event: str,
    data: dict = Body(..., description="Dados a enviar"),
):
    """Dispara webhook para evento específico."""
    eventos_validos = [WebhookEvent.NEW_PUBLICATION, WebhookEvent.CAPTACAO_COMPLETED, WebhookEvent.PROCESS_UPDATE, WebhookEvent.NEW_RESULT]
    
    if event not in eventos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Evento inválido. Use: {eventos_validos}"
        )
    
    result = trigger_webhook(event, data)
    
    return {
        "status": "success",
        "result": result,
    }