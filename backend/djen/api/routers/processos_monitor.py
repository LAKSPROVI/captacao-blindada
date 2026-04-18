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


def get_db() -> Database:
    from djen.api.app import get_database
    return get_database()


@router.get("/listar", summary="Listar processos monitorados")
def listar_processos(
    status: str = Query("ativo", description="Status: ativo, inativo, todos"),
    limite: int = Query(500, ge=1, le=5000),
):
    """Lista todos os processos sendo monitorados automaticamente."""
    db = get_db()
    if status == "todos":
        ativos = db.listar_processos_monitorados(status="ativo", limite=limite)
        inativos = db.listar_processos_monitorados(status="inativo", limite=limite)
        processos = ativos + inativos
    else:
        processos = db.listar_processos_monitorados(status=status, limite=limite)
    return {"status": "success", "total": len(processos), "processos": processos}


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
def verificar_agora(limite: int = Query(20, ge=1, le=100)):
    """Executa verificacao imediata dos processos pendentes via DataJud."""
    from djen.api.app import _run_processos_datajud_cycle
    try:
        result = _run_processos_datajud_cycle(limite=limite)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{numero_processo:path}", summary="Remover processo do monitoramento")
def remover_processo(numero_processo: str):
    """Remove (desativa) um processo do monitoramento automatico."""
    db = get_db()
    ok = db.deletar_processo_monitorado(numero_processo)
    if not ok:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    return {"status": "success", "message": f"Processo {numero_processo} removido do monitoramento"}
