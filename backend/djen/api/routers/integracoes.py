"""
Router de Integrações - CAPTAÇÃO BLINDADA.
Endpoints para integrações externas e automações.
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel

from djen.api.database import Database

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
def telegram_status():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return {
        "status": "success",
        "enabled": bool(token and chat_id),
        "configured": bool(token),
    }


@router.post("/telegram/test", summary="Testar Telegram")
def telegram_test(message: str = Body("Teste Captação Blindada")):
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID não configurados no .env"}
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return {"status": "success" if resp.status_code < 400 else "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# Zapier/n8n Webhook Receiver
# =============================================================================

@router.post("/webhook-receiver", summary="Receber webhook externo")
def webhook_receiver(payload: dict = Body(...)):
    db = get_db()
    try:
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS webhook_received (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                payload TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        db.conn.commit()
    except Exception:
        pass
    
    import json
    db.conn.execute(
        "INSERT INTO webhook_received (source, payload) VALUES (?, ?)",
        (payload.get("source", "unknown"), json.dumps(payload, ensure_ascii=False))
    )
    db.conn.commit()
    return {"status": "success", "message": "Webhook recebido"}


@router.get("/webhook-receiver/logs", summary="Logs de webhooks recebidos")
def webhook_logs(limite: int = Query(50, ge=1, le=500)):
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
def google_calendar_status():
    return {
        "status": "success",
        "enabled": False,
        "message": "Integração com Google Calendar disponível. Configure GOOGLE_CALENDAR_CREDENTIALS no .env",
    }


# =============================================================================
# Status de todas as integrações
# =============================================================================

@router.get("/status", summary="Status de todas as integrações")
def status_integracoes():
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
