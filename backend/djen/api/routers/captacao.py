"""
Router de Captacao Automatizada.

Endpoints para configurar, executar e monitorar captacoes
automatizadas de informacoes do DataJud e DJEN.
"""

import asyncio
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

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

log = logging.getLogger("captacao.api.captacao")

router = APIRouter(prefix="/api/captacao", tags=["Captacao Automatizada"])


# =========================================================================
# Helpers
# =========================================================================

def get_db():
    from djen.api.app import get_database
    return get_database()


def get_service():
    from djen.agents.captacao_service import get_captacao_service
    return get_captacao_service()


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
):
    """Lista todas as captacoes configuradas."""
    db = get_db()
    captacoes = db.listar_captacoes(ativo=ativo, tipo_busca=tipo_busca, prioridade=prioridade)
    return {"status": "success", "total": len(captacoes), "captacoes": captacoes}


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
def executar_todas():
    """Executa todas as captacoes ativas cujo horario/dia permite."""
    service = get_service()
    return service.executar_todas()


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

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
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
    limite: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Lista historico de execucoes de uma captacao."""
    db = get_db()
    execucoes = db.listar_execucoes_captacao(captacao_id, limite=limite, offset=offset)
    return {"status": "success", "total": len(execucoes), "execucoes": execucoes}


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
