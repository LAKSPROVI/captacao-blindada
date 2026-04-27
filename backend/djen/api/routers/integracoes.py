"""
Router de Integrações - CAPTAÇÃO BLINDADA.
Endpoints para integrações externas e automações.
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body, HTTPException, Request
from pydantic import BaseModel

from djen.api.ratelimit import limiter
from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB

log = logging.getLogger("captacao.integracoes")
router = APIRouter(prefix="/api/integracoes", tags=["Integracoes"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


# =============================================================================
# Telegram Bot (placeholder)
# =============================================================================

class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str
    enabled: bool = True


@router.get("/telegram/status", summary="Status do Telegram Bot")
@limiter.limit("60/minute")
def telegram_status(request: Request, current_user: UserInDB = Depends(get_current_user)):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return {
        "status": "success",
        "enabled": bool(token and chat_id),
        "configured": bool(token),
    }


@router.post("/telegram/test", summary="Testar Telegram")
@limiter.limit("5/minute")
def telegram_test(request: Request, message: str = Body("Teste Captação Blindada"), current_user: UserInDB = Depends(get_current_user)):
    import requests as _requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID não configurados no .env"}
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = _requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return {"status": "success" if resp.status_code < 400 else "error", "code": resp.status_code}
    except Exception as e:
        log.error("Erro ao testar Telegram: %s", e, exc_info=True)
        return {"status": "error", "message": "Erro ao consultar servico externo"}


# =============================================================================
# Zapier/n8n Webhook Receiver
# =============================================================================

@router.post("/webhook-receiver", summary="Receber webhook externo")
@limiter.limit("30/minute")
def webhook_receiver(request: Request, payload: dict = Body(...), current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    import json
    db.conn.execute(
        "INSERT INTO webhook_received (source, payload) VALUES (?, ?)",
        (payload.get("source", "unknown"), json.dumps(payload, ensure_ascii=False))
    )
    db.conn.commit()
    return {"status": "success", "message": "Webhook recebido"}


@router.get("/webhook-receiver/logs", summary="Logs de webhooks recebidos")
@limiter.limit("60/minute")
def webhook_logs(request: Request, limite: int = Query(50, ge=1, le=500), current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    try:
        rows = db.conn.execute("SELECT * FROM webhook_received ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return {"status": "success", "total": len(rows), "logs": [dict(r) for r in rows]}
    except Exception:
        return {"status": "success", "total": 0, "logs": []}


# =============================================================================
# Google Calendar (placeholder)
# =============================================================================

@router.get("/google-calendar/status", summary="Status Google Calendar")
@limiter.limit("60/minute")
def google_calendar_status(request: Request):
    return {
        "status": "success",
        "enabled": False,
        "message": "Integração com Google Calendar disponível. Configure GOOGLE_CALENDAR_CREDENTIALS no .env",
    }


# =============================================================================
# Status de todas as integrações
# =============================================================================

@router.get("/status", summary="Status de todas as integrações")
@limiter.limit("60/minute")
def status_integracoes(request: Request, current_user: UserInDB = Depends(get_current_user)):
    return {
        "status": "success",
        "integracoes": {
            "email": {"enabled": bool(os.environ.get("SMTP_HOST")), "type": "SMTP"},
            "whatsapp": {"enabled": bool(os.environ.get("WHATSAPP_TOKEN")), "type": "WhatsApp Business API"},
            "telegram": {"enabled": bool(os.environ.get("TELEGRAM_BOT_TOKEN")), "type": "Telegram Bot"},
            "google_calendar": {"enabled": False, "type": "Google Calendar API"},
            "zapier": {"enabled": True, "type": "Webhook Receiver (Zapier/n8n/Make)"},
            "gemini_ai": {"enabled": True, "type": "Google Gemini API"},
        }
    }
