"""
Router de Notificações - CAPTAÇÃO BLINDADA.
"""
import logging
from fastapi import APIRouter, Body
from djen.api.notifications import get_notification_manager

log = logging.getLogger("captacao.notifications")
router = APIRouter(prefix="/api/notifications", tags=["Notificacoes"])


@router.get("/status", summary="Status das notificações")
def notification_status():
    """Retorna status dos canais de notificação."""
    manager = get_notification_manager()
    return {"status": "success", **manager.get_status()}


@router.post("/test/email", summary="Testar email")
def test_email(to: str = Body(...), subject: str = Body("Teste Captação Blindada")):
    """Envia email de teste."""
    manager = get_notification_manager()
    if not manager.email.enabled:
        return {"status": "error", "message": "SMTP não configurado. Configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD no .env"}
    success = manager.email.send(to, subject, "Este é um email de teste do sistema Captação Blindada.")
    return {"status": "success" if success else "error", "message": "Email enviado" if success else "Falha ao enviar"}


@router.post("/test/whatsapp", summary="Testar WhatsApp")
def test_whatsapp(to: str = Body(...)):
    """Envia mensagem WhatsApp de teste."""
    manager = get_notification_manager()
    if not manager.whatsapp.enabled:
        return {"status": "error", "message": "WhatsApp não configurado. Configure WHATSAPP_TOKEN e WHATSAPP_PHONE_ID no .env"}
    success = manager.whatsapp.send(to, "Teste do sistema Captação Blindada")
    return {"status": "success" if success else "error", "message": "Mensagem enviada" if success else "Falha ao enviar"}
