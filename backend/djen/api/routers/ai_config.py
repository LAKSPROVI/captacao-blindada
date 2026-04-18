from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
from djen.api.database import Database

router = APIRouter(prefix="/ai", tags=["IA & Modelos"])
db = Database()

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
async def list_ai_configs():
    """Lista todas as configuracoes de IA por funcao."""
    try:
        return db.listar_ai_configs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/{function_key}", response_model=AIConfigSchema)
async def get_ai_config(function_key: str):
    """Obtem configuracao de IA para uma funcao especifica."""
    config = db.obter_ai_config(function_key)
    if not config:
        raise HTTPException(status_code=404, detail="Funcao de IA nao encontrada")
    return config

@router.put("/config/{function_key}")
async def update_ai_config(function_key: str, data: AIConfigUpdate):
    """Atualiza a configuracao de IA para uma funcao."""
    try:
        success = db.salvar_ai_config(
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_available_models():
    """Retorna lista de modelos sugeridos por provedor."""
    return {
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI / Gameron",
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "claude-sonnet-4-20250514"]
            },
            {
                "id": "anthropic",
                "name": "Anthropic (Direct)",
                "models": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
            },
            {
                "id": "google",
                "name": "Google Gemini",
                "models": ["gemini-1.5-pro", "gemini-1.5-flash"]
            }
        ]
    }

@router.post("/test")
async def test_ai_config(data: AIConfigUpdate):
    """Testa uma configuracao sem salvar no banco."""
    try:
        from djen.agents.ml_agents import LLMClient
        client = LLMClient(api_key=data.api_key, base_url=data.base_url)
        
        # Override default model if provided
        response = client.chat(
            system_prompt="Voce e um assistente de teste de conectividade. Responda apenas 'OK' em uma linha.",
            user_prompt="Ola, isto e um teste de conexao.",
            model=data.model_name
        )
        
        if response and "OK" in response.upper():
            return {"status": "success", "message": "Conexao estabelecida com sucesso!"}
        else:
            return {
                "status": "warning", 
                "message": "Nao foi possivel obter uma resposta valida do modelo",
                "response": response
            }
    except Exception as e:
        return {"status": "error", "message": f"Erro na conexao: {str(e)}"}
