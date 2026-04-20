"""
Router de Captacao Automatizada.

Endpoints para configurar, executar e monitorar captacoes
automatizadas de informacoes do DataJud e DJEN.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel, Field

from djen.api.schemas import (
    CaptacaoCreateRequest,
    CaptacaoUpdateRequest,
    CaptacaoPreviewRequest,
    CaptacaoResponse,
    ExecucaoCaptacaoResponse,
    CaptacaoStatsResponse,
    PublicacaoResponse,
    DiffResponse,
)

from djen.api.schemas import (
    CaptacaoCreateRequest,
    CaptacaoUpdateRequest,
    CaptacaoPreviewRequest,
    CaptacaoResponse,
    ExecucaoCaptacaoResponse,
    CaptacaoStatsResponse,
    PublicacaoResponse,
    DiffResponse,
)
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.api.captacao")

router = APIRouter(prefix="/api/captacao", tags=["Captacao Automatizada"])

DEFAULT_LIMIT = 100
MAX_LIMIT = 500
HISTORICO_LIMIT = 100
CACHE_TTL_SECONDS = 300

_cached_db = None
_cached_service = None

_captacao_list_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": 0,
    "filters": None
}


# =========================================================================
# Helpers
# =========================================================================

def get_db():
    global _cached_db
    if _cached_db is None:
        from djen.api.database import get_database
        _cached_db = get_database()
    return _cached_db


def get_service():
    global _cached_service
    if _cached_service is None:
        from djen.agents.captacao_service import get_captacao_service
        _cached_service = get_captacao_service()
    return _cached_service


def _get_filter_key(ativo: Optional[bool], tipo_busca: Optional[str], prioridade: Optional[str]) -> str:
    return f"{ativo}:{tipo_busca}:{prioridade}"


def _is_cache_valid(filters_key: str) -> bool:
    now = time.time()
    return (_captacao_list_cache["data"] is not None and
            _captacao_list_cache["filters"] == filters_key and
            now - _captacao_list_cache["timestamp"] < CACHE_TTL_SECONDS)


# =========================================================================
# Rotas fixas (antes das parametrizadas)
# =========================================================================

@router.get("/stats", summary="Estatisticas de captacao")
def stats_captacao():
    """Retorna estatisticas gerais das captacoes."""
    db = get_db()
    return db.obter_stats_captacao()


@router.get("/listar", summary="Listar captacoes")
def listar_captacoes(
    ativo: Optional[bool] = Query(None, description="Filtrar por ativo/inativo"),
    tipo_busca: Optional[str] = Query(None, description="Filtrar por tipo"),
    prioridade: Optional[str] = Query(None, description="Filtrar por prioridade"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginacao"),
    no_cache: bool = Query(False, description="Ignorar cache"),
):
    """Lista todas as captacoes configuradas com cache em memória."""
    db = get_db()
    filters_key = _get_filter_key(ativo, tipo_busca, prioridade)
    
    if no_cache or not _is_cache_valid(filters_key):
        captacoes = db.listar_captacoes(ativo=ativo, tipo_busca=tipo_busca, prioridade=prioridade)
        _captacao_list_cache["data"] = captacoes
        _captacao_list_cache["filters"] = filters_key
        _captacao_list_cache["timestamp"] = time.time()
    
    all_captacoes = _captacao_list_cache["data"]
    total = len(all_captacoes)
    has_more = (offset + limit) < total
    next_offset = offset + limit if has_more else None
    paginated = all_captacoes[offset:offset + limit]
    
    return {
        "status": "success",
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": next_offset,
        "captacoes": paginated
    }


@router.post("/criar", summary="Criar nova captacao")
def criar_captacao(req: CaptacaoCreateRequest):
    """
    Cria uma nova captacao automatizada com parametros de busca.

    Tipos de busca disponiveis:
    - **processo**: por numero de processo CNJ
    - **oab**: por numero de OAB + UF
    - **nome_parte**: por nome de parte processual
    - **nome_advogado**: por nome de advogado
    - **classe**: por codigo de classe processual (DataJud)
    - **assunto**: por codigo de assunto (DataJud)
    - **tribunal_geral**: varredura geral de um tribunal
    """
    db = get_db()
    # Converter fontes enum para string
    fontes_str = ",".join(f.value if hasattr(f, "value") else str(f) for f in req.fontes)
    # Converter tipo_busca e prioridade enum para string
    tipo_busca_str = req.tipo_busca.value if hasattr(req.tipo_busca, "value") else str(req.tipo_busca)
    prioridade_str = req.prioridade.value if hasattr(req.prioridade, "value") else str(req.prioridade)

    captacao_id = db.criar_captacao(
        nome=req.nome,
        descricao=req.descricao,
        tipo_busca=tipo_busca_str,
        numero_processo=req.numero_processo,
        numero_oab=req.numero_oab,
        uf_oab=req.uf_oab,
        nome_parte=req.nome_parte,
        nome_advogado=req.nome_advogado,
        tribunal=req.tribunal,
        tribunais=req.tribunais,
        classe_codigo=req.classe_codigo,
        assunto_codigo=req.assunto_codigo,
        orgao_id=req.orgao_id,
        tipo_comunicacao=req.tipo_comunicacao,
        data_inicio=req.data_inicio,
        data_fim=req.data_fim,
        fontes=fontes_str,
        intervalo_minutos=req.intervalo_minutos,
        horario_inicio=req.horario_inicio,
        horario_fim=req.horario_fim,
        dias_semana=req.dias_semana,
        auto_enriquecer=req.auto_enriquecer,
        notificar_whatsapp=req.notificar_whatsapp,
        notificar_email=req.notificar_email,
        prioridade=prioridade_str,
    )
    if not captacao_id:
        raise HTTPException(status_code=500, detail="Erro ao criar captacao")
    captacao = db.obter_captacao(captacao_id)
    # Retornar diretamente com id no topo para compatibilidade com testes
    result = dict(captacao) if captacao else {}
    result["id"] = captacao_id
    return result


@router.post("/preview", summary="Testar parametros de busca (dry-run)")
def preview_captacao(req: CaptacaoPreviewRequest):
    """
    Executa busca SEM salvar resultados. Util para testar
    parametros antes de criar uma captacao agendada.
    """
    service = get_service()
    return service.preview(req.model_dump())


@router.post("/executar-todas", summary="Executar todas as captacoes pendentes")
@limiter.limit("5/minute")
def executar_todas(request: Request):
    """Executa todas as captacoes ativas cujo horario/dia permite."""
    service = get_service()
    return service.executar_todas()


# =========================================================================
# Relatorio Discreto (_ONLY_ADMIN)
# =========================================================================

@router.get("/resumo", summary="Relatorio compacto do sistema")
def relatorio_sistema():
    """
    Relatorio discreto para acompanhamento do sistema.
    Retorna apenas numeros essenciais para verificacao rapida.
    """
    db = get_db()
    
    stats_gerais = db.obter_stats_captacao()
    
    captacoes_ativas = db.conn.execute(
        "SELECT COUNT(*) as c FROM captacoes WHERE ativo = 1"
    ).fetchone()["c"]
    
    execucoes_hoje = db.conn.execute(
        """SELECT COUNT(*) as c FROM execucoes_captacao 
           WHERE date(inicio) = date('now') AND status = 'completed'"""
    ).fetchone()["c"]
    
    resultados_hoje = db.conn.execute(
        """SELECT COALESCE(SUM(novos_resultados), 0) as t FROM execucoes_captacao 
           WHERE date(inicio) = date('now')"""
    ).fetchone()["t"]
    
    ultimas_execucoes = db.conn.execute(
        """SELECT e.id, e.captacao_id, e.inicio, e.status, e.total_resultados, e.novos_resultados, c.nome
           FROM execucoes_captacao e
           JOIN captacoes c ON e.captacao_id = c.id
           ORDER BY e.inicio DESC
           LIMIT 10"""
    ).fetchall()
    
    captacoes_problema = db.conn.execute(
        """SELECT c.id, c.nome, c.ultima_execucao, c.total_execucoes, c.total_novos
           FROM captacoes c
           WHERE c.ativo = 1 AND (
               c.ultima_execucao IS NULL OR 
               c.ultima_execucao < datetime('now', '-24 hours')
           )
           ORDER BY c.ultima_execucao ASC
           LIMIT 10"""
    ).fetchall()
    
    return {
        "data": datetime.now().isoformat(),
        "captacoes_ativas": captacoes_ativas,
        "execucoes_hoje": execucoes_hoje,
        "resultados_hoje": resultados_hoje,
        "total_novos_all": stats_gerais.get("total_novos_encontrados", 0),
        "ultimas": [dict(e) for e in ultimas_execucoes],
        "pendentes": [dict(c) for c in captacoes_problema] if captacoes_problema else []
    }


# =========================================================================
# Rotas parametrizadas
# =========================================================================

@router.get("/{captacao_id}", summary="Detalhes de uma captacao")
def obter_captacao(captacao_id: int):
    """Retorna detalhes completos de uma captacao."""
    db = get_db()
    captacao = db.obter_captacao(captacao_id)
    if not captacao:
        raise HTTPException(status_code=404, detail="Captacao nao encontrada")
    return dict(captacao)


@router.put("/{captacao_id}", summary="Atualizar captacao")
def atualizar_captacao(captacao_id: int, req: CaptacaoUpdateRequest):
    """Atualiza parametros de uma captacao existente."""
    db = get_db()
    existing = db.obter_captacao(captacao_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Captacao nao encontrada")

    updates = {}
    data = req.model_dump(exclude_unset=True)
    
    for k, v in data.items():
        if v is None:
            continue
        # Converter listas (como fontes) para string separada por virgula
        if isinstance(v, list):
            updates[k] = ",".join(str(item.value if hasattr(item, "value") else item) for item in v)
        # Converter Enums simples para seu valor string
        elif hasattr(v, "value"):
            updates[k] = v.value
        else:
            updates[k] = v

    if not updates:
        return {"status": "success", "message": "Nenhum campo para atualizar"}

    db.atualizar_captacao(captacao_id, **updates)
    captacao = db.obter_captacao(captacao_id)
    return dict(captacao)


@router.delete("/{captacao_id}", summary="Desativar captacao")
def desativar_captacao(captacao_id: int):
    """Desativa uma captacao (soft delete)."""
    db = get_db()
    db.atualizar_captacao(captacao_id, ativo=0)
    return {"status": "success", "message": f"Captacao {captacao_id} desativada"}


@router.post("/{captacao_id}/executar", summary="Executar captacao agora")
def executar_captacao(captacao_id: int):
    """Executa uma captacao imediatamente (sob demanda)."""
    db = get_db()
    captacao = db.obter_captacao(captacao_id)
    if not captacao:
        raise HTTPException(status_code=404, detail="Captacao nao encontrada")
    service = get_service()
    return service.executar(captacao_id)


@router.post("/{captacao_id}/pausar", summary="Pausar captacao")
def pausar_captacao(captacao_id: int):
    """Pausa o scheduler sem desativar."""
    db = get_db()
    db.atualizar_captacao(captacao_id, pausado=1)
    return {"status": "success", "message": f"Captacao {captacao_id} pausada"}


@router.post("/{captacao_id}/retomar", summary="Retomar captacao")
def retomar_captacao(captacao_id: int):
    """Retoma uma captacao pausada."""
    db = get_db()
    db.atualizar_captacao(captacao_id, pausado=0)
    return {"status": "success", "message": f"Captacao {captacao_id} retomada"}


@router.get("/{captacao_id}/historico", summary="Historico de execucoes")
def historico_captacao(
    captacao_id: int,
    limite: int = Query(HISTORICO_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    """Lista historico de execucoes de uma captacao."""
    db = get_db()
    execucoes = db.listar_execucoes_captacao(captacao_id, limite=limite, offset=offset)
    total = db.conn.execute(
        "SELECT COUNT(*) as c FROM execucoes_captacao WHERE captacao_id = ?",
        (captacao_id,)
    ).fetchone()["c"]
    return {"status": "success", "total": total, "limit": limite, "offset": offset, "execucoes": execucoes}


@router.get("/{captacao_id}/resultados", summary="Publicacoes encontradas")
def resultados_captacao(
    captacao_id: int,
    limite: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    fonte: Optional[str] = Query(None),
):
    """Lista publicacoes encontradas por esta captacao."""
    db = get_db()
    pubs = db.buscar_publicacoes_captacao(captacao_id, limite=limite, offset=offset, fonte=fonte)
    return {"status": "success", "total": len(pubs), "publicacoes": pubs}


@router.get("/{captacao_id}/diff", summary="Comparar execucoes")
def diff_captacao(captacao_id: int):
    """Compara ultima execucao vs anterior (novos/mantidos)."""
    service = get_service()
    return service.diff(captacao_id)


# =========================================================================
# WebSocket
# =========================================================================

@router.websocket("/ws/{captacao_id}")
async def websocket_captacao(websocket: WebSocket, captacao_id: int):
    """
    WebSocket para acompanhar captacao em tempo real.

    Eventos:
    - {type: "progress", fonte: "...", total: N, novos: N}
    - {type: "completed", total: N, novos: N, tempo_ms: N}
    - {type: "error", message: "..."}

    Comandos:
    - {action: "start"} - inicia execucao da captacao
    - {action: "status"} - verifica status atual
    """
    await websocket.accept()

    try:
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
                await websocket.send_json({"type": "started", "captacao_id": captacao_id})

                def run():
                    try:
                        service = get_service()
                        return service.executar(captacao_id)
                    except Exception as e:
                        return {"status": "error", "erro": str(e)}

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run)

                if result and result.get("status") == "error":
                    await websocket.send_json({
                        "type": "error",
                        "message": result.get("erro", "Erro desconhecido"),
                    })
                elif result:
                    for exec_info in result.get("execucoes", []):
                        await websocket.send_json({
                            "type": "progress",
                            "fonte": exec_info.get("fonte"),
                            "total": exec_info.get("total_resultados", 0),
                            "novos": exec_info.get("novos_resultados", 0),
                            "status": exec_info.get("status"),
                            "duracao_ms": exec_info.get("duracao_ms", 0),
                        })
                    await websocket.send_json({
                        "type": "completed",
                        "captacao_id": captacao_id,
                        "total": result.get("total_resultados", 0),
                        "novos": result.get("novos_resultados", 0),
                        "tempo_ms": result.get("tempo_total_ms", 0),
                        "processos_enriquecidos": result.get("processos_enriquecidos", []),
                    })

            elif action == "status":
                db = get_db()
                cap = db.obter_captacao(captacao_id)
                if cap:
                    await websocket.send_json({
                        "type": "status",
                        "captacao_id": captacao_id,
                        "ativo": bool(cap.get("ativo")),
                        "pausado": bool(cap.get("pausado")),
                        "ultima_execucao": cap.get("ultima_execucao"),
                        "proxima_execucao": cap.get("proxima_execucao"),
                        "total_execucoes": cap.get("total_execucoes", 0),
                        "total_novos": cap.get("total_novos", 0),
                    })
                else:
                    await websocket.send_json({
                        "type": "error", "message": "Captacao nao encontrada",
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("Captacao WebSocket erro: %s", e)
