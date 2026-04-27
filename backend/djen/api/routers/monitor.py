"""
Captacao Peticao Blindada - Router Monitor.
Endpoints para gerenciamento de monitorados e publicacoes.
"""

import logging
import csv
import io
import json
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body, Request
from fastapi.responses import StreamingResponse

from djen.api.ratelimit import limiter
from djen.api.schemas import (
    MonitoradoCreateRequest, MonitoradoUpdateRequest,
    MonitoradoResponse, PublicacaoResponse, StatsResponse,
)
from djen.api.database import Database
from djen.api.auth import get_current_user, UserInDB

log = logging.getLogger("captacao.monitor")
router = APIRouter(prefix="/api/monitor", tags=["Monitor"])

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def get_db() -> Database:
    from djen.api.database import get_database
    return get_database()


@router.post("/add", response_model=MonitoradoResponse, summary="Adicionar monitorado")
@limiter.limit("30/minute")
def adicionar_monitorado(request: Request, req: MonitoradoCreateRequest):
    """
    Adiciona um novo item para monitoramento automatico.
    Tipos: oab, processo, nome, parte, advogado.
    O scheduler verificara periodicamente novas publicacoes.
    """
    db = get_db()
    fontes_str = ",".join(f.value for f in req.fontes)
    mid = db.adicionar_monitorado(
        tipo=req.tipo.value,
        valor=req.valor,
        nome_amigavel=req.nome_amigavel,
        tribunal=req.tribunal,
        fontes=fontes_str,
        intervalo_minutos=req.intervalo_minutos,
        horario_inicio=req.horario_inicio,
        horario_fim=req.horario_fim,
        dias_semana=req.dias_semana,
    )
    mon = db.obter_monitorado(mid)
    if not mon:
        raise HTTPException(status_code=500, detail="Erro ao criar monitorado")
    mon["total_publicacoes"] = 0
    return MonitoradoResponse(**mon)


@router.get("/list", response_model=List[MonitoradoResponse], summary="Listar monitorados")
@limiter.limit("60/minute")
def listar_monitorados(request: Request, ativos: bool = Query(True, description="Apenas ativos")):
    """Lista todos os itens monitorados."""
    db = get_db()
    monitorados = db.listar_monitorados(apenas_ativos=ativos)
    return [MonitoradoResponse(**m) for m in monitorados]


@router.get("/monitorados", response_model=List[MonitoradoResponse], summary="Listar monitorados (alias)")
@limiter.limit("60/minute")
def listar_monitorados_alias(request: Request, ativos: bool = Query(True, description="Apenas ativos")):
    """Alias para /list - Lista todos os itens monitorados."""
    db = get_db()
    monitorados = db.listar_monitorados(apenas_ativos=ativos)
    return [MonitoradoResponse(**m) for m in monitorados]


@router.get("/publicacoes/recentes", response_model=List[PublicacaoResponse], summary="Publicacoes recentes")
@limiter.limit("60/minute")
def publicacoes_recentes(
    request: Request,
    fonte: Optional[str] = Query(None),
    tribunal: Optional[str] = Query(None),
    processo: Optional[str] = Query(None),
    limite: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Lista publicacoes recentes salvas no banco."""
    db = get_db()
    pubs = db.buscar_publicacoes(fonte=fonte, tribunal=tribunal, processo=processo, limite=limite)
    return [PublicacaoResponse(**p) for p in pubs]


@router.get("/stats", response_model=StatsResponse, summary="Estatisticas")
@limiter.limit("60/minute")
def estatisticas(request: Request):
    """Retorna estatisticas gerais do sistema."""
    db = get_db()
    stats = db.obter_stats()
    return StatsResponse(**stats)




@router.get('/publicacoes/buscar', response_model=List[PublicacaoResponse], summary='Busca textual no banco local')
@limiter.limit("60/minute")
def buscar_publicacoes_texto(
    request: Request,
    termo: str = Query(..., min_length=1, description='Texto a buscar em todos os campos'),
    fonte: str = Query(None),
    tribunal: str = Query(None),
    limite: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Busca full-text nas publicacoes salvas localmente. Pesquisa em processo, conteudo, partes, advogados, OABs, assuntos."""
    db = get_db()
    pubs = db.buscar_publicacoes_texto(termo=termo, fonte=fonte, tribunal=tribunal, limite=limite)
    return [PublicacaoResponse(**p) for p in pubs]

@router.get("/{monitorado_id}", response_model=MonitoradoResponse, summary="Obter monitorado")
@limiter.limit("60/minute")
def obter_monitorado(request: Request, monitorado_id: int):
    db = get_db()
    mon = db.obter_monitorado(monitorado_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitorado nao encontrado")
    count = db.conn.execute(
        "SELECT COUNT(*) as c FROM publicacoes WHERE monitorado_id=?", (monitorado_id,)
    ).fetchone()
    mon["total_publicacoes"] = count["c"] if count else 0
    return MonitoradoResponse(**mon)


@router.put("/{monitorado_id}", response_model=MonitoradoResponse, summary="Atualizar monitorado")
@limiter.limit("30/minute")
def atualizar_monitorado(request: Request, monitorado_id: int, req: MonitoradoUpdateRequest):
    db = get_db()
    kwargs = {}
    if req.nome_amigavel is not None:
        kwargs["nome_amigavel"] = req.nome_amigavel
    if req.ativo is not None:
        kwargs["ativo"] = 1 if req.ativo else 0
    if req.tribunal is not None:
        kwargs["tribunal"] = req.tribunal
    if req.fontes is not None:
        kwargs["fontes"] = ",".join(f.value for f in req.fontes)
    if req.intervalo_minutos is not None:
        kwargs["intervalo_minutos"] = req.intervalo_minutos
    if req.horario_inicio is not None:
        kwargs["horario_inicio"] = req.horario_inicio
    if req.horario_fim is not None:
        kwargs["horario_fim"] = req.horario_fim
    if req.dias_semana is not None:
        kwargs["dias_semana"] = req.dias_semana
    db.atualizar_monitorado(monitorado_id, **kwargs)
    mon = db.obter_monitorado(monitorado_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitorado nao encontrado")
    mon["total_publicacoes"] = 0
    return MonitoradoResponse(**mon)


@router.delete("/{monitorado_id}", summary="Desativar monitorado")
@limiter.limit("30/minute")
def desativar_monitorado(request: Request, monitorado_id: int):
    db = get_db()
    db.desativar_monitorado(monitorado_id)
    return {"status": "ok", "message": f"Monitorado {monitorado_id} desativado"}


# =============================================================================
# Exportação de Publicações
# =============================================================================

@router.get("/publicacoes/export/csv", summary="Exportar publicações em CSV")
@limiter.limit("5/minute")
def exportar_publicacoes_csv(
    request: Request,
    fonte: Optional[str] = Query(None),
    tribunal: Optional[str] = Query(None),
    limite: int = Query(MAX_LIMIT, ge=1, le=5000),
):
    """Exporta publicações em CSV."""
    db = get_db()
    pubs = db.buscar_publicacoes(fonte=fonte, tribunal=tribunal, limite=limite)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Fonte", "Tribunal", "Data", "Processo", "Classe", "Orgao", "OABs", "Advogados", "Partes", "Conteudo"])
    
    for p in pubs:
        writer.writerow([
            p.get("id", ""),
            p.get("fonte", ""),
            p.get("tribunal", ""),
            p.get("data_publicacao", ""),
            p.get("numero_processo", ""),
            p.get("classe_processual", ""),
            p.get("orgao_julgador", ""),
            p.get("oab_encontradas", ""),
            p.get("advogados", ""),
            p.get("partes", ""),
            (p.get("conteudo", "") or "")[:500],
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=publicacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )


@router.get("/publicacoes/export/json", summary="Exportar publicações em JSON")
@limiter.limit("5/minute")
def exportar_publicacoes_json(
    request: Request,
    fonte: Optional[str] = Query(None),
    tribunal: Optional[str] = Query(None),
    limite: int = Query(MAX_LIMIT, ge=1, le=5000),
):
    """Exporta publicações em JSON."""
    db = get_db()
    pubs = db.buscar_publicacoes(fonte=fonte, tribunal=tribunal, limite=limite)
    
    data = json.dumps(pubs, ensure_ascii=False, indent=2, default=str)
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=publicacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.json"}
    )


# =============================================================================
# Marcar publicação como lida/favorita
# =============================================================================

@router.put("/publicacoes/{pub_id}/lida", summary="Marcar publicação como lida")
@limiter.limit("60/minute")
def marcar_lida(request: Request, pub_id: int, lida: bool = Body(True)):
    """Marca/desmarca publicação como lida."""
    db = get_db()
    db.conn.execute("UPDATE publicacoes SET lida = ? WHERE id = ?", (1 if lida else 0, pub_id))
    db.conn.commit()
    return {"status": "success", "id": pub_id, "lida": lida}


@router.put("/publicacoes/{pub_id}/favorita", summary="Favoritar publicação")
@limiter.limit("60/minute")
def marcar_favorita(request: Request, pub_id: int, favorita: bool = Body(True)):
    """Marca/desmarca publicação como favorita."""
    db = get_db()
    db.conn.execute("UPDATE publicacoes SET favorita = ? WHERE id = ?", (1 if favorita else 0, pub_id))
    db.conn.commit()
    return {"status": "success", "id": pub_id, "favorita": favorita}
