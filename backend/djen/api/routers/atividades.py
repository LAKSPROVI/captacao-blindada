"""
Router de Atividades - CAPTAÇÃO BLINDADA.
Log de atividades por usuário e resumo email.
"""
import logging
from datetime import datetime, date
from typing import Optional

from fastapi import Request, APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.atividades")
router = APIRouter(prefix="/api/atividades", tags=["Atividades"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("/usuario/{user_id}", summary="Atividades de um usuário")
@limiter.limit("60/minute")
def atividades_usuario(request: Request, user_id: int, limite: int = Query(50, ge=1, le=500)):
    """Lista atividades recentes de um usuário específico."""
    db = get_db()
    rows = db.conn.execute(
        "SELECT * FROM audit_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limite)
    ).fetchall()
    return {"status": "success", "user_id": user_id, "total": len(rows), "atividades": [dict(r) for r in rows]}


@router.get("/recentes", summary="Atividades recentes do sistema")
@limiter.limit("60/minute")
def atividades_recentes(request: Request, limite: int = Query(50, ge=1, le=500)):
    """Lista atividades recentes de todos os usuários."""
    db = get_db()
    rows = db.conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return {"status": "success", "total": len(rows), "atividades": [dict(r) for r in rows]}


@router.get("/resumo-email", summary="Resumo em HTML para email")
@limiter.limit("60/minute")
def resumo_email(request: Request):
    """Gera resumo do sistema em HTML para envio por email."""
    db = get_db()
    hoje = date.today().strftime("%d/%m/%Y")
    
    captacoes = db.conn.execute("SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1").fetchone()["c"]
    exec_hoje = db.conn.execute("SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio) = date('now','localtime')").fetchone()["c"]
    novos = db.conn.execute("SELECT COALESCE(SUM(novos_resultados),0) as t FROM execucoes_captacao WHERE date(inicio) = date('now','localtime')").fetchone()["t"]
    pub_total = db.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
    erros = db.conn.execute("SELECT COUNT(*) as c FROM system_errors WHERE status='aberto'").fetchone()["c"]
    
    ultimas = db.conn.execute("""
        SELECT e.captacao_id, c.nome, e.inicio, e.status, e.total_resultados, e.novos_resultados
        FROM execucoes_captacao e JOIN captacoes c ON e.captacao_id = c.id
        ORDER BY e.inicio DESC LIMIT 5
    """).fetchall()
    
    exec_html = ""
    for e in ultimas:
        d = dict(e)
        cor = "#22c55e" if d["status"] == "completed" else "#ef4444"
        exec_html += f"""<tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{d['nome']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{d['inicio']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;color:{cor}">{d['status']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right">{d['total_resultados']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:bold">{d['novos_resultados']}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb">
    <div style="background:#1e3a5f;color:white;padding:20px;border-radius:8px 8px 0 0;text-align:center">
        <h1 style="margin:0;font-size:24px">Captação Blindada</h1>
        <p style="margin:5px 0 0;opacity:0.8">Resumo Diário - {hoje}</p>
    </div>
    
    <div style="background:white;padding:20px;border:1px solid #e5e7eb">
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
            <tr>
                <td style="padding:15px;text-align:center;background:#f0f9ff;border-radius:8px">
                    <div style="font-size:28px;font-weight:bold;color:#1e3a5f">{captacoes}</div>
                    <div style="font-size:12px;color:#6b7280">Captações Ativas</div>
                </td>
                <td style="width:10px"></td>
                <td style="padding:15px;text-align:center;background:#f0fdf4;border-radius:8px">
                    <div style="font-size:28px;font-weight:bold;color:#16a34a">{exec_hoje}</div>
                    <div style="font-size:12px;color:#6b7280">Execuções Hoje</div>
                </td>
                <td style="width:10px"></td>
                <td style="padding:15px;text-align:center;background:#fefce8;border-radius:8px">
                    <div style="font-size:28px;font-weight:bold;color:#ca8a04">{novos}</div>
                    <div style="font-size:12px;color:#6b7280">Novos Resultados</div>
                </td>
            </tr>
        </table>
        
        <div style="margin-bottom:15px">
            <span style="font-size:14px;color:#6b7280">Total publicações: <strong>{pub_total}</strong></span>
            {f' | <span style="color:#ef4444;font-size:14px">Erros abertos: <strong>{erros}</strong></span>' if erros > 0 else ''}
        </div>
        
        <h3 style="color:#1e3a5f;border-bottom:2px solid #e5e7eb;padding-bottom:8px">Últimas Execuções</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
            <tr style="background:#f9fafb">
                <th style="padding:8px;text-align:left">Captação</th>
                <th style="padding:8px;text-align:left">Início</th>
                <th style="padding:8px;text-align:left">Status</th>
                <th style="padding:8px;text-align:right">Total</th>
                <th style="padding:8px;text-align:right">Novos</th>
            </tr>
            {exec_html}
        </table>
    </div>
    
    <div style="background:#f3f4f6;padding:15px;border-radius:0 0 8px 8px;text-align:center;font-size:12px;color:#9ca3af">
        Captação Blindada - Sistema de Captação Jurídica Automatizada<br>
        Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")} (Horário de Brasília)
    </div>
</body>
</html>"""
    
    return HTMLResponse(content=html)


@router.get("/duplicatas", summary="Verificar publicações duplicadas")
@limiter.limit("60/minute")
def verificar_duplicatas(request: Request, limite: int = Query(50, ge=1, le=500)):
    """Identifica publicações potencialmente duplicadas."""
    db = get_db()
    rows = db.conn.execute("""
        SELECT numero_processo, tribunal, COUNT(*) as qtd, 
               GROUP_CONCAT(id) as ids
        FROM publicacoes 
        WHERE numero_processo IS NOT NULL
        GROUP BY numero_processo, tribunal
        HAVING COUNT(*) > 1
        ORDER BY qtd DESC
        LIMIT ?
    """, (limite,)).fetchall()
    
    return {
        "status": "success",
        "total_duplicatas": len(rows),
        "duplicatas": [dict(r) for r in rows],
    }
