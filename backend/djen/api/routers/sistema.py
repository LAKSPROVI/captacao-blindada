"""
Router de Versão e Sistema - CAPTAÇÃO BLINDADA.
Informações de versão, changelog e exportação.
"""
import logging
import io
import sqlite3
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from djen.api.database import Database

log = logging.getLogger("captacao.versao")
router = APIRouter(prefix="/api/sistema", tags=["Sistema"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


VERSION = "1.5.0"
BUILD_DATE = "2026-04-23"

CHANGELOG = [
    {"version": "1.5.0", "date": "2026-04-23", "changes": [
        "Agendamento por data específica para captações",
        "Limite configurável por captação (max_resultados, max_paginas)",
        "Log de chamadas IA com estatísticas",
        "Fallback entre modelos IA",
        "Notificação email para erros críticos",
        "Alerta de saldo baixo",
        "Upload CSV de processos",
        "Busca por nome de parte",
        "Suspender/reativar tenant",
        "Sidebar com memória localStorage",
        "Comparação entre tribunais",
        "Top processos mais ativos",
        "95+ implementações no total",
    ]},
    {"version": "1.4.1", "date": "2026-04-23", "changes": [
        "Busca global full-text em todo o sistema",
        "Atividades por usuário com log detalhado",
        "Resumo email HTML template profissional",
        "Detecção de publicações duplicadas",
        "Contadores em tempo real para sidebar",
        "Sistema de favoritos e tags",
        "Agenda de compromissos e audiências",
        "Sistema completo de prazos processuais",
        "40+ métodos API no frontend",
    ]},
    {"version": "1.3.0", "date": "2026-04-22", "changes": [
        "Security headers (X-Frame, XSS, CSP)",
        "CORS restrito configurável",
        "Bloqueio de login após 5 tentativas",
        "Toast notifications, Skeleton, Modal",
        "Exportação CSV/JSON publicações e auditoria",
        "Notificações Email e WhatsApp",
        "Clonar captação com 1 clique",
        "Performance SQLite (WAL, cache, mmap)",
        "Gzip compression",
        "Breadcrumbs e página 404",
    ]},
    {"version": "1.2.1", "date": "2026-04-22", "changes": [
        "Cache em memória com TTL 5 minutos",
        "Paginação automática com has_more/next_offset",
        "Rate Limiting (slowapi)",
        "Circuit Breaker para fontes externas",
        "Validação CNJ, OAB e 62 tribunais",
        "Webhooks com CRUD e trigger",
        "Métricas JSON e Prometheus",
        "2FA TOTP, API Keys, SSO/SAML",
        "Modelos Gemini (3 modelos, 4 funções IA)",
        "Horário de Brasília em todo o sistema",
        "Busca paginada DJEN (até 1000 resultados)",
    ]},
]


@router.get("/versao", summary="Versão do sistema")
def versao():
    """Retorna versão atual e informações do sistema."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "name": "Captação Blindada",
        "description": "Sistema de Captação Jurídica Automatizada",
        "api_docs": "/docs",
    "total_endpoints": 76,
    "total_implementacoes": 115,
    }


@router.get("/changelog", summary="Changelog do sistema")
def changelog():
    """Retorna histórico de mudanças."""
    return {"status": "success", "changelog": CHANGELOG}


@router.get("/exportar-banco", summary="Exportar banco completo")
def exportar_banco():
    """Exporta o banco de dados SQLite completo como download."""
    db = get_db()
    
    output = io.BytesIO()
    backup_conn = sqlite3.connect(":memory:")
    db.conn.backup(backup_conn)
    
    for line in backup_conn.iterdump():
        output.write(f"{line}\n".encode("utf-8"))
    
    backup_conn.close()
    output.seek(0)
    
    filename = f"captacao_blindada_dump_{datetime.now().strftime('%Y%m%d_%H%M')}.sql"
    return StreamingResponse(
        output,
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/tabelas", summary="Listar tabelas e contagens")
def listar_tabelas():
    """Lista todas as tabelas do banco com contagem de registros."""
    db = get_db()
    tables = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    
    resultado = {}
    total_registros = 0
    for t in tables:
        name = t["name"]
        count = db.conn.execute(f"SELECT COUNT(*) as c FROM [{name}]").fetchone()["c"]
        resultado[name] = count
        total_registros += count
    
    return {
        "status": "success",
        "total_tabelas": len(resultado),
        "total_registros": total_registros,
        "tabelas": resultado,
    }
