"""
Router de Notificações - CAPTAÇÃO BLINDADA.
"""
import logging
from fastapi import Request, APIRouter, Depends, Body
from djen.api.notifications import get_notification_manager
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.notifications")
router = APIRouter(prefix="/api/notifications", tags=["Notificacoes"])


@router.get("/status", summary="Status das notificações")
@limiter.limit("60/minute")
def notification_status(request: Request, current_user: UserInDB = Depends(get_current_user)):
    """Retorna status dos canais de notificação."""
    manager = get_notification_manager()
    return {"status": "success", **manager.get_status()}


@router.post("/test/email", summary="Testar email")
@limiter.limit("5/minute")
def test_email(request: Request, to: str = Body(...), subject: str = Body("Teste Captação Blindada"), current_user: UserInDB = Depends(get_current_user)):
    """Envia email de teste."""
    manager = get_notification_manager()
    if not manager.email.enabled:
        return {"status": "error", "message": "SMTP não configurado. Configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD no .env"}
    success = manager.email.send(to, subject, "Este é um email de teste do sistema Captação Blindada.")
    return {"status": "success" if success else "error", "message": "Email enviado" if success else "Falha ao enviar"}


@router.post("/test/whatsapp", summary="Testar WhatsApp")
@limiter.limit("5/minute")
def test_whatsapp(request: Request, to: str = Body(...), current_user: UserInDB = Depends(get_current_user)):
    """Envia mensagem WhatsApp de teste."""
    manager = get_notification_manager()
    if not manager.whatsapp.enabled:
        return {"status": "error", "message": "WhatsApp não configurado. Configure WHATSAPP_TOKEN e WHATSAPP_PHONE_ID no .env"}
    success = manager.whatsapp.send(to, "Teste do sistema Captação Blindada")
    return {"status": "success" if success else "error", "message": "Mensagem enviada" if success else "Falha ao enviar"}
