"""
Captacao Peticao Blindada - Router DJEN.
Endpoints para busca de comunicacoes processuais (texto completo) via API DJEN/CNJ.

API: https://comunicaapi.pje.jus.br/api/v1/comunicacao
Requer IP brasileiro (proxy BR automatico).
"""

import logging
import time
from typing import Optional

from fastapi import Request, APIRouter, Depends, HTTPException, Query

from djen.api.schemas import BuscaDjenRequest, BuscaResponse, PublicacaoResponse
from djen.api.database import Database
from djen.sources.djen_source import DjenSource
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.djen")
router = APIRouter(prefix="/api/djen", tags=["DJEN"])

_source: Optional[DjenSource] = None


def get_source() -> DjenSource:
    global _source
    if _source is None:
        _source = DjenSource()
    return _source


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


def _to_response(pub) -> PublicacaoResponse:
    d = pub.to_dict()
    return PublicacaoResponse(**d)


@router.post("/buscar", response_model=BuscaResponse, summary="Busca geral no DJEN")
@limiter.limit("30/minute")
def buscar_djen(request: Request, req: BuscaDjenRequest, current_user: UserInDB = Depends(get_current_user)):
    """
    Busca comunicacoes processuais no DJEN (CNJ).
    Retorna TEXTO COMPLETO de intimacoes, citacoes e editais.
    Dados incluem: partes, advogados, OABs, orgao julgador.
    """
    source = get_source()
    db = get_db()
    t0 = time.time()

    try:
        resultados = source.buscar(
            termo=req.numero_processo or req.nome_advogado or req.nome_parte or "",
            data_inicio=req.data_inicio,
            data_fim=req.data_fim,
            tribunal=req.tribunal,
            numero_oab=req.numero_oab,
            uf_oab=req.uf_oab,
            nome_advogado=req.nome_advogado,
            nome_parte=req.nome_parte,
            numero_processo=req.numero_processo,
            orgao_id=req.orgao_id,
            meio=req.meio,
            pagina=req.pagina,
            itens_por_pagina=req.itens_por_pagina,
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        termo_log = req.numero_processo or req.numero_oab or req.nome_advogado or ""
        db.registrar_busca("djen", "djen_api", req.tribunal, termo_log,
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="djen_api",
            total=len(resultados),
            tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        log.error("[DJEN] Erro na busca: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Erro ao consultar servico externo")


@router.get("/processo/{numero}", response_model=BuscaResponse, summary="Buscar comunicacoes de um processo")
@limiter.limit("60/minute")
def buscar_por_processo(request: Request, numero: str, current_user: UserInDB = Depends(get_current_user)):
    """Busca todas as comunicacoes (intimacoes/citacoes) de um processo no DJEN."""
    source = get_source()
    db = get_db()
    t0 = time.time()

    try:
        resultados = source.buscar_por_processo(numero)
        elapsed_ms = int((time.time() - t0) * 1000)

        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        db.registrar_busca("processo", "djen_api", None, numero,
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="djen_api",
            total=len(resultados),
            tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        log.error("[DJEN] Erro ao buscar processo %s: %s", numero, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Erro ao consultar servico externo")


@router.get("/oab/{numero}/{uf}", response_model=BuscaResponse, summary="Buscar por OAB")
@limiter.limit("60/minute")
def buscar_por_oab(request: Request, numero: str,
    uf: str,
    data_inicio: Optional[str] = Query(None, description="DD/MM/AAAA"),
    data_fim: Optional[str] = Query(None, description="DD/MM/AAAA"),
    current_user: UserInDB = Depends(get_current_user),
):
    """Busca comunicacoes destinadas a um advogado pela OAB."""
    source = get_source()
    db = get_db()
    t0 = time.time()

    try:
        resultados = source.buscar_por_oab(numero, uf.upper(), data_inicio, data_fim)
        elapsed_ms = int((time.time() - t0) * 1000)

        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        db.registrar_busca("oab", "djen_api", None, f"{numero}/{uf}",
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="djen_api",
            total=len(resultados),
            tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        log.error("[DJEN] Erro ao buscar OAB %s/%s: %s", numero, uf, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Erro ao consultar servico externo")


@router.get("/advogado/{nome}", response_model=BuscaResponse, summary="Buscar por nome de advogado")
@limiter.limit("60/minute")
def buscar_por_advogado(request: Request, nome: str,
    tribunal: Optional[str] = Query(None),
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
):
    """Busca comunicacoes por nome de advogado."""
    source = get_source()
    db = get_db()
    t0 = time.time()
    try:
        resultados = source.buscar_por_advogado(nome, data_inicio, data_fim, tribunal)
        elapsed_ms = int((time.time() - t0) * 1000)

        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        db.registrar_busca("advogado", "djen_api", tribunal, nome,
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="djen_api", total=len(resultados), tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        log.error("[DJEN] Erro ao buscar advogado %s: %s", nome, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Erro ao consultar servico externo")


@router.get("/parte/{nome}", response_model=BuscaResponse, summary="Buscar por nome de parte")
@limiter.limit("60/minute")
def buscar_por_parte(request: Request, nome: str,
    tribunal: Optional[str] = Query(None),
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
):
    """Busca comunicacoes por nome de parte processual."""
    source = get_source()
    db = get_db()
    t0 = time.time()
    try:
        resultados = source.buscar_por_parte(nome, data_inicio, data_fim, tribunal)
        elapsed_ms = int((time.time() - t0) * 1000)

        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        db.registrar_busca("parte", "djen_api", tribunal, nome,
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="djen_api", total=len(resultados), tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        log.error("[DJEN] Erro ao buscar parte %s: %s", nome, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Erro ao consultar servico externo")


@router.get("/tribunais", summary="Listar tribunais do DJEN")
@limiter.limit("60/minute")
def listar_tribunais(request: Request, current_user: UserInDB = Depends(get_current_user)):
    source = get_source()
    tribunais = source.listar_tribunais()
    return {"tribunais": tribunais, "total": len(tribunais)}


@router.get("/health", summary="Health check DJEN")
@limiter.limit("60/minute")
def health_check_djen(request: Request):
    source = get_source()
    db = get_db()
    result = source.health_check()
    db.registrar_health("djen_api", result.get("status", "error"),
                         result.get("latency_ms", 0), result.get("message", ""),
                         result.get("proxy_used", False))
    return result
