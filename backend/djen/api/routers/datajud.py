"""
Captacao Peticao Blindada - Router DataJud.
Endpoints para busca de metadados processuais via API publica do CNJ.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from djen.api.schemas import BuscaDatajudRequest, BuscaResponse, PublicacaoResponse
from djen.api.database import Database
from djen.sources.datajud import DatajudSource

log = logging.getLogger("captacao.datajud")
router = APIRouter(prefix="/api/datajud", tags=["DataJud"])

# Singleton da fonte
_source: Optional[DatajudSource] = None


def get_source() -> DatajudSource:
    global _source
    if _source is None:
        _source = DatajudSource()
    return _source


def get_db() -> Database:
    from djen.api.app import get_database
    return get_database()


def _to_response(pub) -> PublicacaoResponse:
    d = pub.to_dict()
    return PublicacaoResponse(**d)


@router.post("/buscar", response_model=BuscaResponse, summary="Busca geral no DataJud")
def buscar_datajud(req: BuscaDatajudRequest):
    """
    Busca metadados processuais no DataJud (CNJ).
    Retorna informacoes de processos: classe, assuntos, orgao julgador, movimentacoes.
    NAO retorna texto de publicacoes (para isso use o DJEN).
    """
    source = get_source()
    db = get_db()
    t0 = time.time()

    try:
        resultados = source.buscar(
            termo=req.numero_processo or "",
            tribunal=req.tribunal,
            data_inicio=req.data_inicio,
            data_fim=req.data_fim,
            classe_codigo=req.classe_codigo,
            assunto_codigo=req.assunto_codigo,
            orgao_julgador_codigo=req.orgao_julgador_codigo,
            tamanho=req.tamanho,
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        # Salvar no banco
        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        db.registrar_busca("datajud", "datajud", req.tribunal, req.numero_processo or "",
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="datajud",
            total=len(resultados),
            tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        db.registrar_busca("datajud", "datajud", req.tribunal, req.numero_processo or "",
                           0, "erro", elapsed_ms, str(e))
        log.error("[DataJud] Erro na busca: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao consultar DataJud: {e}")


@router.get("/processo/{numero}", response_model=BuscaResponse, summary="Buscar processo por numero")
def buscar_processo(numero: str, tribunal: str = Query(..., description="Sigla do tribunal (ex: tjsp)")):
    """Busca um processo especifico pelo numero no DataJud."""
    source = get_source()
    db = get_db()
    t0 = time.time()

    try:
        resultados = source.buscar(termo=numero, tribunal=tribunal)
        elapsed_ms = int((time.time() - t0) * 1000)

        for pub in resultados:
            db.salvar_publicacao(pub.to_dict())

        db.registrar_busca("processo", "datajud", tribunal, numero,
                           len(resultados), "ok", elapsed_ms)

        return BuscaResponse(
            fonte="datajud",
            total=len(resultados),
            tempo_ms=elapsed_ms,
            resultados=[_to_response(r) for r in resultados],
        )
    except Exception as e:
        log.error("[DataJud] Erro ao buscar processo %s: %s", numero, e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/tribunais", summary="Listar tribunais disponiveis no DataJud")
def listar_tribunais():
    """Lista todos os tribunais disponiveis para consulta no DataJud."""
    source = get_source()
    return {"tribunais": source.listar_tribunais(), "total": len(source.listar_tribunais())}


@router.get("/health", summary="Health check DataJud")
def health_check_datajud():
    """Verifica se a API DataJud esta acessivel."""
    source = get_source()
    db = get_db()
    result = source.health_check()
    db.registrar_health("datajud", result.get("status", "error"),
                         result.get("latency_ms", 0), result.get("message", ""))
    return result
