"""
Router de Processos Monitorados.
Endpoints para listar, consultar e gerenciar processos
automaticamente monitorados via DataJud.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

from djen.api.database import Database

log = logging.getLogger("captacao.processos_monitor")
router = APIRouter(prefix="/api/processos", tags=["Processos Monitorados"])

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.get("/listar", summary="Listar processos monitorados")
def listar_processos(
    status: str = Query("ativo", description="Status: ativo, inativo, todos"),
    limite: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    """Lista todos os processos sendo monitorados automaticamente."""
    db = get_db()
    if status == "todos":
        ativos = db.listar_processos_monitorados(status="ativo", limite=limite)
        inativos = db.listar_processos_monitorados(status="inativo", limite=limite)
        processos = ativos + inativos
    else:
        processos = db.listar_processos_monitorados(status=status, limite=limite)
    return {"status": "success", "total": len(processos), "limit": limite, "offset": offset, "processos": processos}


@router.get("/stats", summary="Estatisticas de processos monitorados")
def stats_processos():
    """Retorna estatisticas dos processos monitorados."""
    db = get_db()
    return db.stats_processos_monitorados()


@router.get("/{numero_processo:path}", summary="Detalhes de processo monitorado")
def obter_processo(numero_processo: str):
    """Retorna detalhes de um processo monitorado, incluindo movimentacoes."""
    db = get_db()
    proc = db.obter_processo_monitorado(numero_processo)
    if not proc:
        raise HTTPException(status_code=404, detail="Processo nao encontrado no monitoramento")
    return proc


@router.post("/registrar", summary="Registrar processo para monitoramento")
def registrar_processo(
    numero_processo: str,
    tribunal: str = None,
):
    """Registra manualmente um processo para monitoramento DataJud."""
    db = get_db()
    pid = db.registrar_processo_monitorado(
        numero_processo=numero_processo,
        tribunal=tribunal,
        origem="manual",
    )
    if pid is None:
        existing = db.obter_processo_monitorado(numero_processo)
        if existing:
            return {"status": "exists", "message": "Processo ja esta sendo monitorado", "processo": existing}
        raise HTTPException(status_code=400, detail="Numero de processo invalido")
    proc = db.obter_processo_monitorado(numero_processo)
    return {"status": "created", "message": "Processo registrado para monitoramento", "processo": proc}


@router.post("/verificar-agora", summary="Verificar processos no DataJud agora")
def verificar_agora(limite: int = Query(1000, ge=1, le=10000)):
    """Executa verificacao imediata dos processos pendentes via DataJud."""
    from djen.api.app import _run_processos_datajud_cycle
    try:
        result = _run_processos_datajud_cycle(limite=limite)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{numero_processo:path}/historico", summary="Historico de verificacoes")
def obter_historico(numero_processo: str, limite: int = Query(50, ge=1, le=200)):
    """Retorna o historico de verificacoes (DataJud e DJEN) de um processo."""
    db = get_db()
    historico = db.listar_historico_processo(numero_processo, limite=limite)
    return {"status": "success", "total": len(historico), "historico": historico}


@router.delete("/{numero_processo:path}", summary="Remover processo do monitoramento")
def remover_processo(numero_processo: str):
    """Remove (desativa) um processo do monitoramento automatico."""
    db = get_db()
    ok = db.deletar_processo_monitorado(numero_processo)
    if not ok:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    return {"status": "success", "message": f"Processo {numero_processo} removido do monitoramento"}
