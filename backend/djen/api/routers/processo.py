"""
Router de Processo Enriquecido - Sistema Multi-Agentes.

Endpoints para analise completa de processos com pipeline de agentes.
Inclui visoes: completa, resumo executivo, timeline, riscos, status.
"""

import asyncio
import json
import logging
from typing import Optional, List

from fastapi import Request, APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from djen.api.ratelimit import limiter
from djen.agents.canonical_model import (
    ProcessoResponse, ProcessoResumoResponse,
    TimelineResponse, RiscoResponse, PipelineStatusResponse,
)
from djen.agents.pipeline_service import get_pipeline_service, get_cache, get_tracker
from djen.api.auth import get_current_user, UserInDB

log = logging.getLogger("captacao.api.processo")

router = APIRouter(prefix="/api/processo", tags=["Processo Multi-Agentes"])

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


# =========================================================================
# Request/Response models
# =========================================================================

class AnalisarRequest(BaseModel):
    numero_processo: str = Field(..., description="Numero do processo CNJ")
    tribunal: Optional[str] = Field(None, description="Sigla do tribunal (auto-detectado se omitido)")
    agents: Optional[List[str]] = Field(None, description="Agentes especificos para executar (None=todos)")
    force_refresh: bool = Field(False, description="Ignorar cache e reprocessar")


class AgentInfoResponse(BaseModel):
    name: str
    description: str
    depends_on: list
    priority: int


class CacheStatsResponse(BaseModel):
    size: int
    max_size: int
    ttl_seconds: int
    keys: List[str]


# =========================================================================
# Rotas fixas primeiro (antes das parametrizadas)
# =========================================================================

@router.get("/agents", summary="Listar agentes disponiveis")
@limiter.limit("60/minute")
def listar_agentes(request: Request):
    """Lista todos os agentes registrados no sistema multi-agentes."""
    service = get_pipeline_service()
    return {
        "status": "success",
        "total": len(service.list_agents()),
        "agents": service.list_agents(),
    }


@router.get("/cache/stats", summary="Estatisticas do cache")
@limiter.limit("60/minute")
def cache_stats(request: Request):
    """Retorna estatisticas do cache em memoria."""
    cache = get_cache()
    return {
        "status": "success",
        "cache": cache.stats(),
    }


@router.get("/resultados", summary="Listar resultados persistidos")
@limiter.limit("60/minute")
def listar_resultados(request: Request, limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginacao"),
    tribunal: Optional[str] = Query(None, description="Filtrar por tribunal"),
    area: Optional[str] = Query(None, description="Filtrar por area juridica"),
    risco: Optional[str] = Query(None, description="Filtrar por nivel de risco"),
    busca: Optional[str] = Query(None, description="Busca texto no resumo executivo"),
):
    """
    Lista todos os resultados de analise persistidos no banco de dados.

    Suporta paginacao, filtros por tribunal/area/risco e busca textual.
    Retorna resumo de cada resultado (sem dados completos).
    """
    service = get_pipeline_service()

    if busca:
        # Busca textual no resumo
        try:
            from djen.agents.pipeline_service import get_resultado_repo
            repo = get_resultado_repo()
            resultados = repo.buscar_texto(busca)
            return {
                "status": "success",
                "busca": busca,
                "total": len(resultados),
                "limit": limit,
                "offset": offset,
                "resultados": resultados[offset:offset + limit],
            }
        except Exception as e:
            log.error("Erro na busca textual: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Erro interno do servidor")

    dados = service.listar_resultados(
        limit=limit, offset=offset,
        tribunal=tribunal, area=area, risco=risco,
    )
    return {
        "status": "success",
        **dados,
    }


@router.get("/resultados/stats", summary="Estatisticas dos resultados persistidos")
@limiter.limit("60/minute")
def stats_resultados(request: Request):
    """Retorna estatisticas sobre os resultados de analise armazenados."""
    try:
        from djen.agents.pipeline_service import get_resultado_repo
        repo = get_resultado_repo()
        return {
            "status": "success",
            "stats": repo.stats(),
        }
    except Exception as e:
        log.error("Erro ao obter stats: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao acessar banco de dados")


@router.delete("/resultados/{numero}", summary="Deletar resultado persistido")
@limiter.limit("30/minute")
def deletar_resultado(request: Request, numero: str):
    """Remove um resultado de analise do banco de dados."""
    try:
        from djen.agents.pipeline_service import get_resultado_repo
        repo = get_resultado_repo()
        deleted = repo.deletar(numero)
        if not deleted:
            raise HTTPException(status_code=404, detail="Resultado nao encontrado")
        return {"status": "success", "message": f"Resultado deletado para {numero}"}
    except HTTPException:
        raise
    except Exception as e:
        log.error("Erro ao deletar resultado: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao acessar banco de dados")


@router.delete("/cache", summary="Limpar cache")
@limiter.limit("30/minute")
def limpar_cache(request: Request):
    """Limpa todo o cache em memoria."""
    cache = get_cache()
    cache.clear()
    return {"status": "success", "message": "Cache limpo"}


@router.post("/analisar", summary="Analisar processo com pipeline multi-agentes")
@limiter.limit("30/minute")
def analisar_processo(request: AnalisarRequest):
    """
    Executa o pipeline completo de agentes sobre um processo judicial.

    O pipeline inclui:
    - Validacao e normalizacao do numero
    - Coleta de dados do DataJud e DJEN
    - Extracao de entidades, valores e prazos
    - Analise de movimentacoes, cronologia e risco
    - Jurisprudencia correlata e conformidade legal
    - Previsao de resultado
    - Geracao de resumo executivo

    Retorna o ProcessoCanonical completamente enriquecido.
    """
    try:
        service = get_pipeline_service()
        processo = service.analisar(
            numero_processo=request.numero_processo,
            tribunal=request.tribunal,
            agent_names=request.agents,
            force_refresh=request.force_refresh,
        )
        return ProcessoResponse(
            status="success",
            processo=processo,
            visao="completa",
            tempo_processamento_ms=processo.processing_time_ms or 0,
        )
    except Exception as e:
        log.error("Erro ao analisar processo %s: %s", request.numero_processo, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# =========================================================================
# Rotas parametrizadas
# =========================================================================

@router.get("/{numero}", summary="Obter processo enriquecido")
@limiter.limit("60/minute")
def obter_processo(request: Request, numero: str,
    tribunal: Optional[str] = Query(None, description="Sigla do tribunal"),
    force_refresh: bool = Query(False, description="Ignorar cache"),
):
    """
    Obtem analise completa de um processo.
    Se ja estiver no cache, retorna imediatamente.
    Se nao, executa o pipeline completo.
    """
    try:
        service = get_pipeline_service()
        processo = service.analisar(
            numero_processo=numero,
            tribunal=tribunal,
            force_refresh=force_refresh,
        )
        return ProcessoResponse(
            status="success",
            processo=processo,
            visao="completa",
            tempo_processamento_ms=processo.processing_time_ms or 0,
        )
    except Exception as e:
        log.error("Erro ao obter processo %s: %s", numero, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/{numero}/resumo", summary="Visao executiva do processo")
@limiter.limit("60/minute")
def resumo_processo(request: Request, numero: str,
    tribunal: Optional[str] = Query(None),
):
    """Retorna visao executiva resumida do processo."""
    try:
        service = get_pipeline_service()
        processo = service.analisar(numero_processo=numero, tribunal=tribunal)
        return service.get_resumo(processo)
    except Exception as e:
        log.error("Erro ao gerar resumo %s: %s", numero, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/{numero}/timeline", summary="Timeline do processo")
@limiter.limit("60/minute")
def timeline_processo(request: Request, numero: str,
    tribunal: Optional[str] = Query(None),
    min_relevancia: int = Query(1, ge=1, le=10, description="Relevancia minima dos eventos"),
):
    """Retorna timeline interativa com eventos processuais."""
    try:
        service = get_pipeline_service()
        processo = service.analisar(numero_processo=numero, tribunal=tribunal)
        timeline_resp = service.get_timeline(processo)

        # Filtrar por relevancia
        if min_relevancia > 1:
            timeline_resp.timeline = [
                e for e in timeline_resp.timeline if e.relevancia >= min_relevancia
            ]
            timeline_resp.total_eventos = len(timeline_resp.timeline)

        return timeline_resp
    except Exception as e:
        log.error("Erro ao gerar timeline %s: %s", numero, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/{numero}/riscos", summary="Indicadores de risco do processo")
@limiter.limit("60/minute")
def riscos_processo(request: Request, numero: str,
    tribunal: Optional[str] = Query(None),
):
    """Retorna analise de riscos multidimensional do processo."""
    try:
        service = get_pipeline_service()
        processo = service.analisar(numero_processo=numero, tribunal=tribunal)
        return service.get_riscos(processo)
    except Exception as e:
        log.error("Erro ao analisar riscos %s: %s", numero, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/{numero}/status", summary="Status do pipeline de analise")
@limiter.limit("60/minute")
def status_pipeline(request: Request, numero: str):
    """Retorna status atual do pipeline de analise (para polling)."""
    service = get_pipeline_service()
    status = service.get_pipeline_status(numero)
    if not status:
        raise HTTPException(status_code=404, detail="Pipeline nao encontrado para este processo")
    return status


@router.delete("/{numero}/cache", summary="Invalidar cache de um processo")
@limiter.limit("30/minute")
def invalidar_cache_processo(request: Request, numero: str):
    """Remove um processo especifico do cache."""
    cache = get_cache()
    cache.invalidate(numero)
    return {"status": "success", "message": f"Cache invalidado para {numero}"}


# =========================================================================
# WebSocket para progresso em tempo real
# =========================================================================

@router.websocket("/ws/{numero}")
async def websocket_progresso(websocket: WebSocket, numero: str):
    """
    WebSocket para acompanhar progresso do pipeline em tempo real.

    Eventos emitidos:
    - {"type": "progress", "agent": "...", "status": "...", "progress": N}
    - {"type": "completed", "status": "completed", "progress": 100}
    - {"type": "error", "message": "..."}

    O cliente pode enviar:
    - {"action": "start", "tribunal": "...", "force_refresh": true}
      para iniciar uma analise
    - {"action": "status"}
      para verificar status atual
    """
    await websocket.accept()
    tracker = get_tracker()
    event_queue = asyncio.Queue()

    def on_event(event):
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                event_queue.put_nowait, event
            )
        except Exception:
            pass

    tracker.subscribe(numero, on_event)

    try:
        # Task para enviar eventos do tracker
        async def send_events():
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    await websocket.send_json(event)
                    if event.get("type") == "completed":
                        break
                except asyncio.TimeoutError:
                    # Enviar heartbeat
                    try:
                        await websocket.send_json({"type": "heartbeat"})
                    except Exception:
                        break
                except Exception:
                    break

        sender_task = asyncio.create_task(send_events())

        # Receber comandos do cliente
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "error", "message": "Timeout"})
                break
            except WebSocketDisconnect:
                break

            action = data.get("action", "")

            if action == "start":
                # Iniciar analise em background thread
                tribunal = data.get("tribunal")
                force_refresh = data.get("force_refresh", False)

                await websocket.send_json({
                    "type": "started",
                    "numero_processo": numero,
                })

                def run_pipeline():
                    try:
                        service = get_pipeline_service()
                        service.analisar(
                            numero_processo=numero,
                            tribunal=tribunal,
                            force_refresh=force_refresh,
                        )
                    except Exception as e:
                        log.error("Pipeline WebSocket erro: %s", e)

                import threading
                t = threading.Thread(target=run_pipeline, daemon=True)
                t.start()

            elif action == "status":
                service = get_pipeline_service()
                status = service.get_pipeline_status(numero)
                if status:
                    await websocket.send_json({
                        "type": "status",
                        "data": status.model_dump(),
                    })
                else:
                    await websocket.send_json({
                        "type": "status",
                        "data": None,
                    })

        sender_task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("WebSocket erro: %s", e)
    finally:
        tracker.unsubscribe(numero, on_event)
