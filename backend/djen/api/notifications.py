"""
Notificações para CAPTAÇÃO BLINDADA.

Sistema de notificações por Email e WhatsApp.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List
from dataclasses import dataclass
import requests

log = logging.getLogger("captacao.notifications")


# =============================================================================
# Email
# =============================================================================

class EmailNotifier:
    """Envia notificações por email via SMTP."""
    
    def __init__(self):
        self.host = os.environ.get("SMTP_HOST", "")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.from_addr = os.environ.get("SMTP_FROM", self.user)
        self.enabled = bool(self.host and self.user)
    
    def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        """Envia email."""
        if not self.enabled:
            log.warning("[Email] SMTP não configurado")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = to
            
            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))
            
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            
            log.info(f"[Email] Enviado para {to}: {subject}")
            return True
        except Exception as e:
            log.error(f"[Email] Erro: {e}")
            return False


# =============================================================================
# WhatsApp (via API)
# =============================================================================

class WhatsAppNotifier:
    """Envia notificações via WhatsApp Business API."""
    
    def __init__(self):
        self.token = os.environ.get("WHATSAPP_TOKEN", "")
        self.phone_id = os.environ.get("WHATSAPP_PHONE_ID", "")
        self.enabled = bool(self.token and self.phone_id)
    
    def send(self, to: str, message: str) -> bool:
        """Envia mensagem WhatsApp."""
        if not self.enabled:
            log.warning("[WhatsApp] API não configurada")
            return False
        try:
            url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code < 400:
                log.info(f"[WhatsApp] Enviado para {to}")
                return True
            log.error(f"[WhatsApp] Erro {resp.status_code}: {resp.text[:200]}")
            return False
        except Exception as e:
            log.error(f"[WhatsApp] Erro: {e}")
            return False


# =============================================================================
# Notification Manager
# =============================================================================

class NotificationManager:
    """Gerenciador central de notificações."""
    
    def __init__(self):
        self.email = EmailNotifier()
        self.whatsapp = WhatsAppNotifier()
    
    def notify_new_publication(self, pub: Dict, captacao_nome: str = "") -> Dict:
        """Notifica sobre nova publicação encontrada."""
        results = {"email": False, "whatsapp": False}
        
        processo = pub.get("numero_processo", "N/A")
        tribunal = pub.get("tribunal", "N/A")
        conteudo = (pub.get("conteudo", "") or "")[:300]
        
        subject = f"[Captação Blindada] Nova publicação - {processo}"
        body = f"""Nova publicação encontrada!

Captação: {captacao_nome}
Processo: {processo}
Tribunal: {tribunal}
Data: {pub.get('data_publicacao', 'N/A')}

Conteúdo:
{conteudo}

---
Sistema Captação Blindada
"""
        # Email (se configurado)
        email_to = os.environ.get("NOTIFICATION_EMAIL", "")
        if email_to and self.email.enabled:
            results["email"] = self.email.send(email_to, subject, body)
        
        # WhatsApp (se configurado)
        whatsapp_to = os.environ.get("NOTIFICATION_WHATSAPP", "")
        if whatsapp_to and self.whatsapp.enabled:
            msg = f"*Captação Blindada*\n\nNova publicação!\nProcesso: {processo}\nTribunal: {tribunal}\nCaptação: {captacao_nome}"
            results["whatsapp"] = self.whatsapp.send(whatsapp_to, msg)
        
        return results
    
    def get_status(self) -> Dict:
        """Retorna status das notificações."""
        return {
            "email": {"enabled": self.email.enabled, "host": self.email.host or "não configurado"},
            "whatsapp": {"enabled": self.whatsapp.enabled},
        }


# =============================================================================
# Instância Global
# =============================================================================

_manager: Optional[NotificationManager] = None

def get_notification_manager() -> NotificationManager:
    global _manager
    if _manager is None:
        _manager = NotificationManager()
    return _manager

log.info("Notification manager loaded")
