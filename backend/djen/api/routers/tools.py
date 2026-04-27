"""
Router de Ferramentas - CAPTAÇÃO BLINDADA.
Endpoints utilitários para o sistema.
"""
import logging
import re
from datetime import date, timedelta, datetime
from typing import Optional

from fastapi import Request, APIRouter, Depends, Query, Body

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.tools")
router = APIRouter(prefix="/api/tools", tags=["Ferramentas"])


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.post("/formatar-cnj", summary="Formatar número CNJ")
@limiter.limit("30/minute")
def formatar_cnj(request: Request, numero: str = Body(...)):
    """Formata número de processo para padrão CNJ."""
    numeros = re.sub(r"\D", "", numero)
    if len(numeros) == 20:
        formatted = f"{numeros[:7]}-{numeros[7:9]}.{numeros[9:13]}.{numeros[13]}.{numeros[14:16]}.{numeros[16:]}"
        return {"status": "success", "original": numero, "formatado": formatted}
    return {"status": "error", "message": "Número deve ter 20 dígitos", "original": numero}


@router.post("/calcular-dias-uteis", summary="Calcular dias úteis entre datas")
@limiter.limit("30/minute")
def calcular_dias_uteis(request: Request, data_inicio: str = Body(...),
    data_fim: str = Body(...),
):
    """Calcula quantidade de dias úteis entre duas datas."""
    FERIADOS = [(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(12,25)]
    try:
        dt_ini = date.fromisoformat(data_inicio)
        dt_fim = date.fromisoformat(data_fim)
    except ValueError:
        return {"status": "error", "message": "Datas inválidas. Use YYYY-MM-DD"}
    
    dias_uteis = 0
    dt = dt_ini
    while dt <= dt_fim:
        if dt.weekday() < 5 and (dt.month, dt.day) not in FERIADOS:
            dias_uteis += 1
        dt += timedelta(days=1)
    
    return {
        "status": "success",
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "dias_corridos": (dt_fim - dt_ini).days,
        "dias_uteis": dias_uteis,
    }


@router.get("/estatisticas-gerais", summary="Estatísticas gerais do sistema")
@limiter.limit("60/minute")
def estatisticas_gerais(request: Request):
    """Retorna estatísticas gerais consolidadas."""
    db = get_db()
    stats = {}
    
    queries = {
        "publicacoes": "SELECT COUNT(*) as c FROM publicacoes",
        "captacoes": "SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1",
        "execucoes": "SELECT COUNT(*) as c FROM execucoes_captacao",
        "erros_abertos": "SELECT COUNT(*) as c FROM system_errors WHERE status = 'aberto'",
        "audit_logs": "SELECT COUNT(*) as c FROM audit_logs",
        "usuarios": "SELECT COUNT(*) as c FROM users",
        "tenants": "SELECT COUNT(*) as c FROM tenants",
    }
    
    for key, query in queries.items():
        try:
            stats[key] = db.conn.execute(query).fetchone()["c"]
        except Exception:
            stats[key] = 0
    
    optional = {
        "prazos": "SELECT COUNT(*) as c FROM prazos WHERE status = 'ativo'",
        "agenda": "SELECT COUNT(*) as c FROM agenda WHERE status = 'pendente'",
        "favoritos": "SELECT COUNT(*) as c FROM favoritos",
        "tags": "SELECT COUNT(*) as c FROM tags",
        "anotacoes": "SELECT COUNT(*) as c FROM processo_anotacoes",
    }
    
    for key, query in optional.items():
        try:
            stats[key] = db.conn.execute(query).fetchone()["c"]
        except Exception:
            stats[key] = 0
    
    return {"status": "success", "stats": stats}


@router.get("/uptime", summary="Uptime do sistema")
@limiter.limit("60/minute")
def uptime(request: Request):
    """Retorna uptime e informações de runtime."""
    import os, platform, sys
    from djen.api.metrics import get_metrics
    m = get_metrics()
    s = m.get_stats()
    return {
        "status": "success",
        "uptime_seconds": s.get("uptime_seconds", 0),
        "requests_total": s.get("requests_total", 0),
        "error_rate": s.get("error_rate", 0),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pid": os.getpid(),
        "datetime": datetime.now().isoformat(),
    }


@router.get("/indices-db", summary="Listar índices do banco")
@limiter.limit("60/minute")
def listar_indices(request: Request):
    """Lista todos os índices do banco de dados."""
    db = get_db()
    rows = db.conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name").fetchall()
    return {"status": "success", "total": len(rows), "indices": [dict(r) for r in rows]}


@router.post("/vacuum", summary="Otimizar banco de dados")
@limiter.limit("5/minute")
def vacuum_db(request: Request):
    """Executa VACUUM no banco para otimizar espaço."""
    db = get_db()
    try:
        size_before = db.conn.execute("SELECT page_count * page_size as s FROM pragma_page_count(), pragma_page_size()").fetchone()["s"]
        db.conn.execute("VACUUM")
        size_after = db.conn.execute("SELECT page_count * page_size as s FROM pragma_page_count(), pragma_page_size()").fetchone()["s"]
        return {
            "status": "success",
            "size_before_mb": round(size_before / 1024 / 1024, 2),
            "size_after_mb": round(size_after / 1024 / 1024, 2),
            "saved_mb": round((size_before - size_after) / 1024 / 1024, 2),
        }
    except Exception as e:
        log.error("Erro ao executar VACUUM: %s", e, exc_info=True)
        return {"status": "error", "message": "Erro ao acessar banco de dados"}
