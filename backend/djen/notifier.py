"""
Notifier - Sistema de notificacao de publicacoes judiciais.

Envia notificacoes via:
- WhatsApp (via OpenClaw plugin Baileys)
- Email (via Gmail/gog CLI)
- Log (fallback)
"""

import json
import os
import subprocess
import logging
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

log = logging.getLogger("djen.notifier")


class Notifier:
    """Gerenciador de notificacoes para publicacoes judiciais."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.log = logging.getLogger("djen.notifier")

        # Configuracoes
        self.whatsapp_enabled = self.config.get("whatsapp_enabled", True)
        self.email_enabled = self.config.get("email_enabled", True)
        self.whatsapp_numbers = self.config.get("whatsapp_numbers", [])
        self.email_recipients = self.config.get("email_recipients", [])
        self.gog_account = self.config.get("gog_account", "navegacaonouniverso@gmail.com")
        self.openclaw_home = self.config.get("openclaw_home", "/opt/CAPTAÇÃO BLINDADA/.openclaw")

    def notificar_publicacoes(self, publicacoes: List[Dict], conn: sqlite3.Connection) -> int:
        """
        Envia notificacoes para publicacoes nao notificadas.

        Args:
            publicacoes: Lista de dicts com dados das publicacoes
            conn: Conexao SQLite para marcar como notificadas

        Returns:
            Numero de publicacoes notificadas com sucesso
        """
        if not publicacoes:
            self.log.info("[Notifier] Nenhuma publicacao para notificar")
            return 0

        # Formatar mensagem
        mensagem = self._formatar_mensagem(publicacoes)

        sucesso = 0

        # Enviar WhatsApp
        if self.whatsapp_enabled and self.whatsapp_numbers:
            for numero in self.whatsapp_numbers:
                if self._enviar_whatsapp(numero, mensagem):
                    sucesso += 1

        # Enviar Email
        if self.email_enabled and self.email_recipients:
            assunto = f"DJen Monitor - {len(publicacoes)} nova(s) publicacao(oes) - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            for email in self.email_recipients:
                if self._enviar_email(email, assunto, mensagem):
                    sucesso += 1

        # Sempre logar
        self.log.info("[Notifier] %d publicacoes notificadas", len(publicacoes))

        # Marcar como notificadas
        ids_notificados = [p.get("id") for p in publicacoes if p.get("id")]
        if ids_notificados and conn:
            self._marcar_notificadas(conn, ids_notificados)

        return sucesso

    def _formatar_mensagem(self, publicacoes: List[Dict]) -> str:
        """Formata publicacoes em mensagem legivel."""
        linhas = []
        linhas.append(f"=== DJEN MONITOR - {len(publicacoes)} NOVA(S) PUBLICACAO(OES) ===")
        linhas.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        linhas.append("")

        for i, pub in enumerate(publicacoes[:10], 1):  # Limitar a 10
            linhas.append(f"--- #{i} ---")
            linhas.append(f"Fonte: {pub.get('fonte', 'N/A').upper()}")
            linhas.append(f"Tribunal: {pub.get('tribunal', 'N/A')}")
            linhas.append(f"Data: {pub.get('data_publicacao', 'N/A')}")

            if pub.get("numero_processo"):
                linhas.append(f"Processo: {pub['numero_processo']}")

            if pub.get("monitorado_nome"):
                linhas.append(f"Monitorado: {pub['monitorado_nome']}")

            # Conteudo resumido
            conteudo = pub.get("conteudo", "")
            if len(conteudo) > 300:
                conteudo = conteudo[:300] + "..."
            linhas.append(f"Conteudo: {conteudo}")

            if pub.get("url_origem"):
                linhas.append(f"URL: {pub['url_origem']}")

            linhas.append("")

        if len(publicacoes) > 10:
            linhas.append(f"... e mais {len(publicacoes) - 10} publicacao(oes)")

        return "\n".join(linhas)

    def _enviar_whatsapp(self, numero: str, mensagem: str) -> bool:
        """
        Envia mensagem via WhatsApp usando OpenClaw.

        O OpenClaw com plugin WhatsApp expoe uma API interna.
        Alternativa: usar o CLI do OpenClaw diretamente.
        """
        try:
            # Metodo 1: Via API HTTP do OpenClaw Gateway
            import requests
            response = requests.post(
                "http://127.0.0.1:18789/api/v1/channels/whatsapp/send",
                json={
                    "to": numero,
                    "message": mensagem[:4000],  # Limite do WhatsApp
                },
                timeout=30,
            )
            if response.status_code in (200, 201, 202):
                self.log.info("[WhatsApp] Mensagem enviada para %s", numero)
                return True
            else:
                self.log.warning("[WhatsApp] HTTP %d ao enviar para %s",
                                 response.status_code, numero)
        except Exception as e:
            self.log.warning("[WhatsApp] Erro via API: %s", e)

        # Metodo 2: Via CLI do OpenClaw (fallback)
        try:
            cmd = [
                "openclaw", "channels", "send",
                "--channel", "whatsapp",
                "--to", numero,
                "--message", mensagem[:4000],
            ]
            env = {
                **os.environ,
                "OPENCLAW_HOME": str(self.openclaw_home),
            }
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, env=env
            )
            if result.returncode == 0:
                self.log.info("[WhatsApp] Mensagem enviada via CLI para %s", numero)
                return True
            else:
                self.log.error("[WhatsApp] CLI erro: %s", result.stderr)
        except Exception as e:
            self.log.error("[WhatsApp] Erro via CLI: %s", e)

        return False

    def _enviar_email(self, destinatario: str, assunto: str, corpo: str) -> bool:
        """
        Envia email via gog CLI (Gmail).
        """
        try:
            # Via gog CLI
            cmd = [
                "gog", "gmail", "send",
                "--to", destinatario,
                "--subject", assunto,
                "--body", corpo[:50000],
            ]
            env = {
                "GOG_KEYRING_PASSWORD": self.config.get(
                    "gog_keyring_password", "cf0b77375a2cf3c62fcbef4dc174c8fe"
                ),
                "GOG_ACCOUNT": self.gog_account,
                "PATH": "/usr/local/bin:/usr/local/go/bin:/usr/bin:/bin",
                "HOME": "/root",
            }
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, env=env
            )
            if result.returncode == 0:
                self.log.info("[Email] Enviado para %s", destinatario)
                return True
            else:
                self.log.error("[Email] gog erro: %s", result.stderr)
        except FileNotFoundError:
            self.log.warning("[Email] gog CLI nao encontrado")
        except Exception as e:
            self.log.error("[Email] Erro: %s", e)

        return False

    def _marcar_notificadas(self, conn: sqlite3.Connection, ids: List[int]):
        """Marca publicacoes como notificadas no banco."""
        for pub_id in ids:
            try:
                conn.execute(
                    "UPDATE publicacoes SET notificado = 1 WHERE id = ?",
                    (pub_id,)
                )
            except Exception as e:
                self.log.error("[Notifier] Erro ao marcar #%d: %s", pub_id, e)
        conn.commit()


class NotificationConfig:
    """
    Gerenciador de configuracao de notificacoes.
    Armazena em JSON no diretorio de config do DJen.
    """

    DEFAULT_PATH = Path("/opt/CAPTAÇÃO BLINDADA/djen/config/notifications.json")

    def __init__(self, config_path: Optional[Path] = None):
        self.path = config_path or self.DEFAULT_PATH
        self._config = self._load()

    def _load(self) -> Dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {
            "whatsapp_enabled": True,
            "email_enabled": True,
            "whatsapp_numbers": [],
            "email_recipients": [],
            "notify_on_new": True,
            "min_relevance": 0,
            "quiet_hours": {"start": 22, "end": 7},
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._config, indent=2, ensure_ascii=False))

    def add_whatsapp(self, numero: str):
        if numero not in self._config["whatsapp_numbers"]:
            self._config["whatsapp_numbers"].append(numero)
            self.save()

    def add_email(self, email: str):
        if email not in self._config["email_recipients"]:
            self._config["email_recipients"].append(email)
            self.save()

    def remove_whatsapp(self, numero: str):
        self._config["whatsapp_numbers"] = [
            n for n in self._config["whatsapp_numbers"] if n != numero
        ]
        self.save()

    def remove_email(self, email: str):
        self._config["email_recipients"] = [
            e for e in self._config["email_recipients"] if e != email
        ]
        self.save()

    def get_notifier(self) -> Notifier:
        return Notifier(config=self._config)

    @property
    def config(self) -> Dict:
        return self._config.copy()

