from fastapi import Request, APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
from djen.api.database import get_database
from djen.api.auth import get_current_user, UserInDB
import logging
import os
from djen.api.ratelimit import limiter

log = logging.getLogger("captacao.ai_config")

router = APIRouter(prefix="/ai", tags=["IA & Modelos"])

# Chave do sistema (Gemini) - OBRIGATÓRIO configurar via env
DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if not DEFAULT_GEMINI_KEY:
    log.warning("GEMINI_API_KEY nao configurada! Funcoes de IA estarao indisponiveis.")

# Modelos testados e funcionando
GEMINI_MODELS = [
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "description": "Rápido e versátil. Melhor custo-benefício para tarefas gerais.",
        "input_tokens": 1048576,
        "output_tokens": 65536,
        "thinking": True,
        "recommended_for": ["resumo", "classificacao"],
    },
    {
        "id": "gemini-3-flash-preview",
        "name": "Gemini 3 Flash Preview",
        "description": "Última geração Flash. Mais inteligente com thinking avançado.",
        "input_tokens": 1048576,
        "output_tokens": 65536,
        "thinking": True,
        "recommended_for": ["previsao", "jurisprudencia"],
    },
    {
        "id": "gemini-2.5-flash-lite",
        "name": "Gemini 2.5 Flash Lite",
        "description": "Ultra leve e econômico. Ideal para tarefas simples e rápidas.",
        "input_tokens": 1048576,
        "output_tokens": 65536,
        "thinking": True,
        "recommended_for": ["classificacao"],
    },
]

# Funções do sistema que usam IA
AI_FUNCTIONS = {
    "classificacao": {
        "label": "Classificação Jurídica",
        "description": "Classifica automaticamente o tipo e área de atuação de cada processo (cível, criminal, trabalhista, etc). Analisa o conteúdo da publicação e identifica a natureza jurídica.",
        "default_model": "gemini-2.5-flash",
    },
    "previsao": {
        "label": "Previsão de Resultado",
        "description": "Estima a probabilidade de resultado favorável baseado em jurisprudência similar. Analisa padrões de decisões anteriores em casos semelhantes.",
        "default_model": "gemini-3-flash-preview",
    },
    "resumo": {
        "label": "Resumo Executivo",
        "description": "Gera resumos executivos claros e objetivos das publicações e movimentações processuais. Extrai os pontos mais relevantes de cada documento.",
        "default_model": "gemini-2.5-flash",
    },
    "jurisprudencia": {
        "label": "Análise de Jurisprudência",
        "description": "Analisa e correlaciona jurisprudência relevante para cada caso. Identifica precedentes, teses e tendências de julgamento nos tribunais.",
        "default_model": "gemini-3-flash-preview",
    },
}

class AIConfigSchema(BaseModel):
    function_key: str
    provider: str
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True
    updated_at: Optional[str] = None

class AIConfigUpdate(BaseModel):
    provider: str
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True

@router.get("/config", response_model=List[AIConfigSchema])
@limiter.limit("60/minute")
async def list_ai_configs(request: Request):
    """Lista todas as configuracoes de IA por funcao."""
    try:
        return get_database().listar_ai_configs()
    except Exception as e:
        log.error("Erro ao listar configs IA: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/config/{function_key}", response_model=AIConfigSchema)
@limiter.limit("60/minute")
async def get_ai_config(request: Request, function_key: str):
    """Obtem configuracao de IA para uma funcao especifica."""
    config = get_database().obter_ai_config(function_key)
    if not config:
        raise HTTPException(status_code=404, detail="Funcao de IA nao encontrada")
    return config

@router.put("/config/{function_key}")
@limiter.limit("30/minute")
async def update_ai_config(request: Request, function_key: str, data: AIConfigUpdate):
    """Atualiza a configuracao de IA para uma funcao."""
    try:
        success = get_database().salvar_ai_config(
            function_key=function_key,
            provider=data.provider,
            model_name=data.model_name,
            api_key=data.api_key,
            base_url=data.base_url,
            enabled=data.enabled
        )
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao atualizar configuracao")
        return {"status": "success", "message": f"Configuracao de {function_key} atualizada"}
    except HTTPException:
        raise
    except Exception as e:
        log.error("Erro ao atualizar config IA %s: %s", function_key, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/models")
@limiter.limit("60/minute")
async def list_available_models(request: Request):
    """Retorna lista de modelos disponíveis e testados."""
    return {
        "providers": [
            {
                "id": "gemini",
                "name": "Google Gemini",
                "models": [m["id"] for m in GEMINI_MODELS],
                "details": GEMINI_MODELS,
                "api_key_configured": bool(DEFAULT_GEMINI_KEY),
            },
        ]
    }

@router.get("/functions")
@limiter.limit("60/minute")
async def list_ai_functions(request: Request):
    """Retorna lista de funções do sistema que usam IA com descrições."""
    return {
        "functions": [
            {
                "key": key,
                "label": info["label"],
                "description": info["description"],
                "default_model": info["default_model"],
            }
            for key, info in AI_FUNCTIONS.items()
        ],
        "models": GEMINI_MODELS,
    }

@router.post("/test")
@limiter.limit("5/minute")
async def test_ai_config(request: Request, data: AIConfigUpdate):
    """Testa uma configuracao sem salvar no banco."""
    try:
        from djen.agents.ml_agents import LLMClient
        
        # Usa chave padrão se não fornecida
        api_key = data.api_key or DEFAULT_GEMINI_KEY
        base_url = data.base_url or "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        
        client = LLMClient(api_key=api_key, base_url=base_url)
        
        response = client.chat(
            system_prompt="Voce e um assistente de teste de conectividade. Responda apenas 'OK' em uma linha.",
            user_prompt="Ola, isto e um teste de conexao.",
            model=data.model_name
        )
        
        if response and "OK" in response.upper():
            return {"status": "success", "message": "Conexao estabelecida com sucesso!", "response": response}
        else:
            return {
                "status": "warning", 
                "message": "Resposta recebida mas diferente do esperado",
                "response": response
            }
    except Exception as e:
        log.error("Erro ao testar config IA: %s", e, exc_info=True)
        return {"status": "error", "message": "Erro na conexao com o servico de IA"}


# =============================================================================
# Log de Chamadas IA
# =============================================================================

@router.get("/logs", summary="Log de chamadas à IA")
@limiter.limit("60/minute")
async def listar_ia_logs(request: Request, limite: int = 50):
    """Lista log de chamadas à IA."""
    _db = get_database()
    # Tabela ia_logs criada em _init_schema
    rows = _db.conn.execute("SELECT * FROM ia_logs ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return {"status": "success", "total": len(rows), "logs": [dict(r) for r in rows]}


@router.get("/logs/stats", summary="Estatísticas de uso da IA")
@limiter.limit("60/minute")
async def ia_stats(request: Request):
    """Estatísticas de uso da IA."""
    _db = get_database()
    try:
        total = _db.conn.execute("SELECT COUNT(*) as c FROM ia_logs").fetchone()["c"]
        tokens_in = _db.conn.execute("SELECT COALESCE(SUM(input_tokens),0) as t FROM ia_logs").fetchone()["t"]
        tokens_out = _db.conn.execute("SELECT COALESCE(SUM(output_tokens),0) as t FROM ia_logs").fetchone()["t"]
        avg_dur = _db.conn.execute("SELECT COALESCE(AVG(duration_ms),0) as t FROM ia_logs").fetchone()["t"]
        por_modelo = _db.conn.execute("SELECT model, COUNT(*) as c, SUM(input_tokens) as inp, SUM(output_tokens) as outp FROM ia_logs GROUP BY model").fetchall()
        por_funcao = _db.conn.execute("SELECT function_key, COUNT(*) as c FROM ia_logs GROUP BY function_key").fetchall()
        erros = _db.conn.execute("SELECT COUNT(*) as c FROM ia_logs WHERE status = 'error'").fetchone()["c"]
        return {
            "status": "success", "total_chamadas": total, "total_input_tokens": tokens_in,
            "total_output_tokens": tokens_out, "avg_duration_ms": round(avg_dur), "erros": erros,
            "por_modelo": [dict(r) for r in por_modelo], "por_funcao": [dict(r) for r in por_funcao],
        }
    except Exception:
        return {"status": "success", "total_chamadas": 0, "total_input_tokens": 0, "total_output_tokens": 0}


@router.get("/fallback-config", summary="Configuração de fallback entre modelos")
@limiter.limit("60/minute")
async def get_fallback_config(request: Request):
    """Retorna cadeia de fallback entre modelos."""
    return {
        "status": "success",
        "fallback_chain": [
            {"model": "gemini-2.5-flash", "priority": 1, "desc": "Principal"},
            {"model": "gemini-3-flash-preview", "priority": 2, "desc": "Fallback"},
            {"model": "gemini-2.5-flash-lite", "priority": 3, "desc": "Último recurso"},
        ],
        "max_retries": 3, "timeout_seconds": 30,
    }
