"""
Router de Busca Unificada - CAPTAÇÃO BLINDADA.
Busca simultânea em múltiplas fontes com merge de resultados.
"""
import logging
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import Request, APIRouter, Depends, Query, Body
from pydantic import BaseModel
from djen.api.auth import get_current_user, UserInDB
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.busca_unificada")
router = APIRouter(prefix="/api/busca", tags=["Busca Unificada"])


class BuscaUnificadaRequest(BaseModel):
    termo: str
    tribunal: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    fontes: list = ["datajud", "djen_api"]
    limite_por_fonte: int = 50


@router.post("/simultanea", summary="Busca simultânea em múltiplas fontes")
@limiter.limit("30/minute")
def busca_simultanea(request: Request, req: BuscaUnificadaRequest):
    """
    Busca em DataJud e DJEN simultaneamente e faz merge dos resultados.
    Retorna resultados unificados com indicação da fonte.
    """
    from djen.api.database import get_database
    db = get_database()
    
    resultados = []
    erros = []
    tempos = {}
    t0 = time.time()
    
    def buscar_datajud():
        try:
            from djen.sources.datajud import DatajudSource
            source = DatajudSource()
            t_start = time.time()
            results = source.buscar(
                termo=req.termo,
                tribunal=req.tribunal,
                data_inicio=req.data_inicio,
                data_fim=req.data_fim,
                tamanho=req.limite_por_fonte,
            )
            elapsed = int((time.time() - t_start) * 1000)
            return {"fonte": "datajud", "resultados": [r.to_dict() for r in results], "tempo_ms": elapsed}
        except Exception as e:
            return {"fonte": "datajud", "erro": str(e), "tempo_ms": 0}
    
    def buscar_djen():
        try:
            from djen.sources.djen_source import DjenSource
            source = DjenSource()
            t_start = time.time()
            results = source.buscar(
                termo=req.termo,
                tribunal=req.tribunal,
                data_inicio=req.data_inicio,
                data_fim=req.data_fim,
                max_results=req.limite_por_fonte,
            )
            elapsed = int((time.time() - t_start) * 1000)
            return {"fonte": "djen_api", "resultados": [r.to_dict() for r in results], "tempo_ms": elapsed}
        except Exception as e:
            return {"fonte": "djen_api", "erro": str(e), "tempo_ms": 0}
    
    # Executar em paralelo
    tasks = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        if "datajud" in req.fontes:
            tasks["datajud"] = executor.submit(buscar_datajud)
        if "djen_api" in req.fontes:
            tasks["djen_api"] = executor.submit(buscar_djen)
        
        for fonte, future in tasks.items():
            try:
                result = future.result(timeout=30)
                if "erro" in result:
                    erros.append({"fonte": result["fonte"], "erro": result["erro"]})
                else:
                    tempos[result["fonte"]] = result["tempo_ms"]
                    for r in result["resultados"]:
                        r["_fonte"] = result["fonte"]
                        resultados.append(r)
            except Exception as e:
                erros.append({"fonte": fonte, "erro": str(e)})
    
    total_ms = int((time.time() - t0) * 1000)
    
    # Registrar busca
    try:
        db.registrar_busca(
            "unificada", "simultanea", req.tribunal or "todos",
            req.termo, len(resultados), "ok" if not erros else "parcial", total_ms
        )
    except Exception:
        pass
    
    return {
        "status": "success",
        "termo": req.termo,
        "total": len(resultados),
        "fontes_consultadas": list(tempos.keys()),
        "tempos_ms": tempos,
        "tempo_total_ms": total_ms,
        "erros": erros if erros else None,
        "resultados": resultados,
    }


@router.get("/status-fontes", summary="Status de todas as fontes")
@limiter.limit("60/minute")
def status_fontes(request: Request):
    """Verifica status de todas as fontes de dados."""
    fontes = []
    
    # DataJud
    try:
        from djen.sources.datajud import DatajudSource
        source = DatajudSource()
        t0 = time.time()
        source.health_check()
        elapsed = int((time.time() - t0) * 1000)
        fontes.append({"fonte": "datajud", "status": "ok", "latency_ms": elapsed})
    except Exception as e:
        fontes.append({"fonte": "datajud", "status": "error", "erro": str(e)})
    
    # DJEN
    try:
        from djen.sources.djen_source import DjenSource
        source = DjenSource()
        t0 = time.time()
        source.health_check()
        elapsed = int((time.time() - t0) * 1000)
        fontes.append({"fonte": "djen_api", "status": "ok", "latency_ms": elapsed})
    except Exception as e:
        fontes.append({"fonte": "djen_api", "status": "error", "erro": str(e)})
    
    ok_count = sum(1 for f in fontes if f["status"] == "ok")
    
    return {
        "status": "ok" if ok_count == len(fontes) else "degraded" if ok_count > 0 else "error",
        "total_fontes": len(fontes),
        "fontes_ok": ok_count,
        "fontes": fontes,
    }
