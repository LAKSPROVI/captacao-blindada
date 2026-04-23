"""
Router de Configuração de Fontes - CAPTAÇÃO BLINDADA.
Endpoints para configurar e gerenciar fontes de dados.
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

log = logging.getLogger("captacao.fontes_config")
router = APIRouter(prefix="/api/fontes", tags=["Fontes de Dados"])


FONTES_DISPONIVEIS = {
    "datajud": {
        "nome": "DataJud (CNJ)",
        "descricao": "API pública do CNJ para metadados processuais",
        "tipo": "api_publica",
        "url": "https://api-publica.datajud.cnj.jus.br",
        "requer_credencial": False,
        "status": "ativo",
    },
    "djen_api": {
        "nome": "DJEN (Diário de Justiça Eletrônico)",
        "descricao": "Diário de Justiça Eletrônico Nacional",
        "tipo": "api_publica",
        "url": "https://comunicaapi.pje.jus.br",
        "requer_credencial": False,
        "status": "ativo",
    },
    "tjsp_dje": {
        "nome": "TJSP DJe",
        "descricao": "Diário de Justiça Eletrônico do TJSP",
        "tipo": "web_scraping",
        "url": "https://dje.tjsp.jus.br",
        "requer_credencial": True,
        "status": "disponivel",
        "env_var": "TJSP_COOKIE_SESSION",
    },
    "dejt": {
        "nome": "DEJT (Diário Eletrônico da Justiça do Trabalho)",
        "descricao": "Publicações da Justiça do Trabalho",
        "tipo": "api",
        "url": "https://dejt.jt.jus.br",
        "requer_credencial": False,
        "status": "disponivel",
    },
    "querido_diario": {
        "nome": "Querido Diário",
        "descricao": "Diários oficiais municipais (Open Knowledge Brasil)",
        "tipo": "api_publica",
        "url": "https://queridodiario.ok.org.br/api",
        "requer_credencial": False,
        "status": "disponivel",
        "env_var": "QUERIDO_DIARIO_API_KEY",
    },
    "jusbrasil": {
        "nome": "JusBrasil",
        "descricao": "Plataforma jurídica com jurisprudência e diários",
        "tipo": "api",
        "url": "https://api.jusbrasil.com.br",
        "requer_credencial": True,
        "status": "disponivel",
        "env_var": "JUSBRASIL_API_KEY",
    },
    "pje": {
        "nome": "PJe (Processo Judicial Eletrônico)",
        "descricao": "Sistema processual eletrônico do CNJ",
        "tipo": "api",
        "url": "https://pje.jus.br",
        "requer_credencial": True,
        "status": "planejado",
    },
    "esaj": {
        "nome": "e-SAJ (São Paulo)",
        "descricao": "Sistema de Automação da Justiça de SP",
        "tipo": "web_scraping",
        "url": "https://esaj.tjsp.jus.br",
        "requer_credencial": True,
        "status": "planejado",
    },
    "projudi": {
        "nome": "PROJUDI",
        "descricao": "Processo Judicial Digital",
        "tipo": "web_scraping",
        "url": "https://projudi.tjpr.jus.br",
        "requer_credencial": True,
        "status": "planejado",
    },
    "dou": {
        "nome": "DOU (Diário Oficial da União)",
        "descricao": "Publicações do Diário Oficial da União",
        "tipo": "api_publica",
        "url": "https://www.in.gov.br/servicos/diario-oficial-da-uniao",
        "requer_credencial": False,
        "status": "planejado",
    },
}


@router.get("/disponiveis", summary="Listar fontes disponíveis")
def listar_fontes():
    """Lista todas as fontes de dados disponíveis e seu status."""
    fontes = []
    for key, info in FONTES_DISPONIVEIS.items():
        fonte = {**info, "id": key}
        if "env_var" in info:
            fonte["credencial_configurada"] = bool(os.environ.get(info["env_var"]))
        fontes.append(fonte)
    
    ativas = sum(1 for f in fontes if f["status"] == "ativo")
    disponiveis = sum(1 for f in fontes if f["status"] == "disponivel")
    planejadas = sum(1 for f in fontes if f["status"] == "planejado")
    
    return {
        "status": "success",
        "total": len(fontes),
        "ativas": ativas,
        "disponiveis": disponiveis,
        "planejadas": planejadas,
        "fontes": fontes,
    }


@router.get("/{fonte_id}", summary="Detalhes de uma fonte")
def detalhe_fonte(fonte_id: str):
    """Retorna detalhes de uma fonte específica."""
    if fonte_id not in FONTES_DISPONIVEIS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Fonte não encontrada")
    
    info = FONTES_DISPONIVEIS[fonte_id]
    fonte = {**info, "id": fonte_id}
    if "env_var" in info:
        fonte["credencial_configurada"] = bool(os.environ.get(info["env_var"]))
    
    return {"status": "success", "fonte": fonte}


@router.get("/ativas/status", summary="Status das fontes ativas")
def status_fontes_ativas():
    """Verifica status de conectividade das fontes ativas."""
    import time
    resultados = []
    
    for key, info in FONTES_DISPONIVEIS.items():
        if info["status"] != "ativo":
            continue
        
        t0 = time.time()
        try:
            if key == "datajud":
                from djen.sources.datajud import DatajudSource
                source = DatajudSource()
                source.health_check()
                latency = int((time.time() - t0) * 1000)
                resultados.append({"id": key, "nome": info["nome"], "status": "ok", "latency_ms": latency})
            elif key == "djen_api":
                from djen.sources.djen_source import DjenSource
                source = DjenSource()
                source.health_check()
                latency = int((time.time() - t0) * 1000)
                resultados.append({"id": key, "nome": info["nome"], "status": "ok", "latency_ms": latency})
        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            resultados.append({"id": key, "nome": info["nome"], "status": "error", "latency_ms": latency, "erro": str(e)[:100]})
    
    ok = sum(1 for r in resultados if r["status"] == "ok")
    return {
        "status": "ok" if ok == len(resultados) else "degraded" if ok > 0 else "error",
        "fontes_ok": ok,
        "total": len(resultados),
        "resultados": resultados,
    }
