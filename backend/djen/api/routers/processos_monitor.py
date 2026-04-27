"""
Router de Processos Monitorados.
Endpoints para listar, consultar e gerenciar processos
automaticamente monitorados via DataJud.
"""

import logging
import json
from typing import Optional, List
from datetime import datetime

from fastapi import Request, APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.processos_monitor")
router = APIRouter(prefix="/api/processos", tags=["Processos Monitorados"])

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


def _tid(user: UserInDB) -> "int | None":
    """Retorna tenant_id para filtragem. Master ve tudo (None)."""
    return None if user.role == "master" else user.tenant_id


# =============================================================================
# Models
# =============================================================================

class ProcessoManualRequest(BaseModel):
    numero_processo: str
    nome: Optional[str] = None
    tribunal: Optional[str] = None


class AnotacaoRequest(BaseModel):
    texto: str
    tipo: str = "nota"


# =============================================================================
# Rotas FIXAS (devem vir ANTES de /{numero_processo:path})
# =============================================================================

@router.get("/listar", summary="Listar processos monitorados")
@limiter.limit("60/minute")
def listar_processos(request: Request, status: str = Query("ativo", description="Status: ativo, inativo, todos"),
    limite: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: UserInDB = Depends(get_current_user),
):
    """Lista todos os processos sendo monitorados automaticamente."""
    db = get_db()
    tid = _tid(current_user)
    if status == "todos":
        ativos = db.listar_processos_monitorados(status="ativo", limite=limite, tenant_id=tid)
        inativos = db.listar_processos_monitorados(status="inativo", limite=limite, tenant_id=tid)
        processos = ativos + inativos
    else:
        processos = db.listar_processos_monitorados(status=status, limite=limite, tenant_id=tid)
    return {"status": "success", "total": len(processos), "limit": limite, "offset": offset, "processos": processos}


@router.get("/stats", summary="Estatisticas de processos monitorados")
@limiter.limit("60/minute")
def stats_processos(request: Request, current_user: UserInDB = Depends(get_current_user)):
    """Retorna estatisticas dos processos monitorados."""
    db = get_db()
    return db.stats_processos_monitorados(tenant_id=_tid(current_user))


@router.post("/adicionar", summary="Adicionar processo manualmente")
@limiter.limit("30/minute")
def adicionar_processo_manual(request: Request, req: ProcessoManualRequest, current_user: UserInDB = Depends(get_current_user)):
    """Adiciona processo por número CNJ para monitoramento."""
    from djen.api.validation import validate_cnj
    
    result = validate_cnj(req.numero_processo)
    if not result.valid:
        raise HTTPException(status_code=400, detail=result.message)
    
    db = get_db()
    pid = db.registrar_processo_monitorado(
        numero_processo=result.value or req.numero_processo,
        tribunal=req.tribunal,
        origem="manual",
        tenant_id=current_user.tenant_id,
    )
    if pid is None:
        existing = db.obter_processo_monitorado(req.numero_processo)
        if existing:
            return {"status": "exists", "message": "Processo já está sendo monitorado", "processo": existing}
        raise HTTPException(status_code=400, detail="Erro ao registrar processo")
    
    proc = db.obter_processo_monitorado(req.numero_processo)
    return {"status": "created", "message": "Processo registrado para monitoramento", "processo": proc}


@router.post("/registrar", summary="Registrar processo para monitoramento")
@limiter.limit("30/minute")
def registrar_processo(request: Request, numero_processo: str,
    tribunal: str = None,
    current_user: UserInDB = Depends(get_current_user),
):
    """Registra manualmente um processo para monitoramento DataJud."""
    db = get_db()
    pid = db.registrar_processo_monitorado(
        numero_processo=numero_processo,
        tribunal=tribunal,
        origem="manual",
        tenant_id=current_user.tenant_id,
    )
    if pid is None:
        existing = db.obter_processo_monitorado(numero_processo)
        if existing:
            return {"status": "exists", "message": "Processo ja esta sendo monitorado", "processo": existing}
        raise HTTPException(status_code=400, detail="Numero de processo invalido")
    proc = db.obter_processo_monitorado(numero_processo)
    return {"status": "created", "message": "Processo registrado para monitoramento", "processo": proc}


@router.post("/verificar-agora", summary="Verificar processos no DataJud agora")
@limiter.limit("30/minute")
def verificar_agora(request: Request, limite: int = Query(1000, ge=1, le=10000)):
    """Executa verificacao imediata dos processos pendentes via DataJud."""
    from djen.api.app import _run_processos_datajud_cycle
    try:
        result = _run_processos_datajud_cycle(limite=limite)
        return {"status": "success", **result}
    except Exception as e:
        log.error("Erro ao verificar processos DataJud: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/buscas/historico", summary="Histórico de buscas realizadas")
@limiter.limit("60/minute")
def historico_buscas(request: Request, limite: int = Query(50, ge=1, le=500)):
    """Lista histórico de buscas realizadas no sistema."""
    db = get_db()
    rows = db.conn.execute(
        "SELECT * FROM buscas ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()
    return {"status": "success", "total": len(rows), "buscas": [dict(r) for r in rows]}


@router.get("/buscar-por-parte", summary="Buscar por nome de parte")
@limiter.limit("60/minute")
def buscar_por_parte(request: Request, nome: str = Query(..., min_length=3, description="Nome da parte"),
    limite: int = Query(50, ge=1, le=500),
):
    """Busca publicações por nome de parte ou advogado."""
    db = get_db()
    termo = f"%{nome}%"
    rows = db.conn.execute("""
        SELECT DISTINCT numero_processo, tribunal, partes, advogados,
               COUNT(*) as total_publicacoes, MAX(data_publicacao) as ultima
        FROM publicacoes
        WHERE partes LIKE ? OR advogados LIKE ? OR conteudo LIKE ?
        GROUP BY numero_processo
        ORDER BY total_publicacoes DESC
        LIMIT ?
    """, (termo, termo, termo, limite)).fetchall()
    return {"status": "success", "nome": nome, "total": len(rows), "processos": [dict(r) for r in rows]}


@router.post("/prazos/calcular", summary="Calcular prazo processual")
@limiter.limit("30/minute")
def calcular_prazo(request: Request, data_inicio: str = Body(..., description="Data início (YYYY-MM-DD)"),
    dias_uteis: int = Body(..., description="Quantidade de dias úteis"),
):
    """Calcula prazo processual em dias úteis (exclui fins de semana e feriados nacionais)."""
    from datetime import date, timedelta
    
    FERIADOS_NACIONAIS = [
        (1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25),
    ]
    
    try:
        dt = date.fromisoformat(data_inicio)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use formato YYYY-MM-DD")
    
    dias_contados = 0
    data_atual = dt
    
    while dias_contados < dias_uteis:
        data_atual += timedelta(days=1)
        if data_atual.weekday() >= 5:
            continue
        if (data_atual.month, data_atual.day) in FERIADOS_NACIONAIS:
            continue
        dias_contados += 1
    
    return {
        "status": "success",
        "data_inicio": data_inicio,
        "dias_uteis": dias_uteis,
        "data_fim": data_atual.isoformat(),
        "dia_semana": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][data_atual.weekday()],
        "dias_corridos": (data_atual - dt).days,
    }


# =============================================================================
# Rotas com PATH PARAMETER (devem vir POR ÚLTIMO)
# =============================================================================

@router.get("/{numero_processo:path}/historico", summary="Historico de verificacoes")
@limiter.limit("60/minute")
def obter_historico(request: Request, numero_processo: str, limite: int = Query(50, ge=1, le=200)):
    """Retorna o historico de verificacoes (DataJud e DJEN) de um processo."""
    db = get_db()
    historico = db.listar_historico_processo(numero_processo, limite=limite)
    return {"status": "success", "total": len(historico), "historico": historico}


@router.get("/{numero_processo:path}/anotacoes", summary="Listar anotações do processo")
@limiter.limit("60/minute")
def listar_anotacoes(request: Request, numero_processo: str, limite: int = Query(100, ge=1, le=500)):
    """Lista anotações/comentários de um processo."""
    db = get_db()
    rows = db.conn.execute(
        "SELECT * FROM processo_anotacoes WHERE numero_processo = ? ORDER BY id DESC LIMIT ?",
        (numero_processo, limite)
    ).fetchall()
    return {"status": "success", "total": len(rows), "anotacoes": [dict(r) for r in rows]}


@router.post("/{numero_processo:path}/anotacoes", summary="Adicionar anotação ao processo")
@limiter.limit("30/minute")
def adicionar_anotacao(request: Request, numero_processo: str, req: AnotacaoRequest):
    """Adiciona anotação/comentário a um processo."""
    db = get_db()
    cur = db.conn.execute(
        "INSERT INTO processo_anotacoes (numero_processo, texto, tipo) VALUES (?, ?, ?)",
        (numero_processo, req.texto, req.tipo)
    )
    db.conn.commit()
    return {"status": "success", "id": cur.lastrowid, "message": "Anotação adicionada"}


@router.delete("/{numero_processo:path}/anotacoes/{anotacao_id}", summary="Remover anotação")
@limiter.limit("30/minute")
def remover_anotacao(request: Request, numero_processo: str, anotacao_id: int):
    """Remove uma anotação de um processo."""
    db = get_db()
    db.conn.execute("DELETE FROM processo_anotacoes WHERE id = ? AND numero_processo = ?", (anotacao_id, numero_processo))
    db.conn.commit()
    return {"status": "success", "message": "Anotação removida"}


@router.delete("/{numero_processo:path}", summary="Remover processo do monitoramento")
@limiter.limit("30/minute")
def remover_processo(request: Request, numero_processo: str):
    """Remove (desativa) um processo do monitoramento automatico."""
    db = get_db()
    ok = db.deletar_processo_monitorado(numero_processo)
    if not ok:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    return {"status": "success", "message": f"Processo {numero_processo} removido do monitoramento"}


@router.get("/{numero_processo:path}", summary="Detalhes de processo monitorado")
@limiter.limit("60/minute")
def obter_processo(request: Request, numero_processo: str):
    """Retorna detalhes de um processo monitorado, incluindo movimentacoes."""
    db = get_db()
    proc = db.obter_processo_monitorado(numero_processo)
    if not proc:
        raise HTTPException(status_code=404, detail="Processo nao encontrado no monitoramento")
    return proc
