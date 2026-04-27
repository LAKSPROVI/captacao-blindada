"""
Router de Validação - CAPTAÇÃO BLINDADA.

Endpoints para validação de campos e listagem de tribunais.
"""
import logging
from typing import Optional

from fastapi import Request, APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from djen.api.auth import get_current_user, UserInDB

from djen.api.ratelimit import limiter
from djen.api.validation import (
    validate_cnj,
    validate_oab,
    validate_tribunal,
    get_tribunais,
    CNJValidator,
    OABValidator,
    ValidationResult,
)

log = logging.getLogger("captacao.validation")
router = APIRouter(prefix="/api/validation", tags=["Validacao"])


# =============================================================================
# Tribunais
# =============================================================================

@router.get("/tribunais", summary="Listar tribunais disponíveis")
@limiter.limit("60/minute")
def listar_tribunais(request: Request, tipo: Optional[str] = Query(None, description="Filtrar por tipo: federal, estadual, trabalho, superior"),
):
    """
    Retorna lista de tribunais disponíveis para consulta.
    
    Use o 'sigla' retornado nos campos de busca.
    """
    tribunais = get_tribunais(tipo)
    return {
        "status": "success",
        "total": len(tribunais),
        "tribunais": tribunais,
    }


@router.get("/tribunais/{sigla}", summary="Verificar tribunal")
@limiter.limit("60/minute")
def verificar_tribunal(request: Request, sigla: str):
    """Verifica se um tribunal existe."""
    result = validate_tribunal(sigla)
    
    if result.valid:
        return {
            "status": "success",
            "valid": True,
            "sigla": result.value,
            "nome": result.message,
        }
    
    raise HTTPException(
        status_code=404,
        detail={
            "valid": False,
            "message": result.message,
            "sigla": sigla,
        }
    )


# =============================================================================
# Validações
# =============================================================================

@router.post("/cnj", summary="Validar número de processo CNJ")
@limiter.limit("30/minute")
def validar_cnj(request: Request, numero_processo: str = Query(..., description="Número do processo CNJ")):
    """
    Valida formato de número de processo CNJ.
    
    Formato: NNNNNNN-DD.YYYY.D.T.RO.AAAA
    Exemplo: 0000832-56.2018.8.10.0001
    """
    result = validate_cnj(numero_processo)
    
    return result.to_dict()


@router.post("/oab", summary="Validar número de OAB")
@limiter.limit("30/minute")
def validar_oab(request: Request, numero_oab: str = Query(..., description="Número da OAB"),
    uf: Optional[str] = Query(None, description="UF da OAB (opcional)"),
):
    """
    Valida formato de número de OAB.
    
    Formato: UF+numero (ex: SP123456)
    """
    result = validate_oab(numero_oab, uf)
    
    return result.to_dict()


class ValidateAllRequest(BaseModel):
    """Request para validar múltiplos campos."""
    numero_processo: Optional[str] = None
    numero_oab: Optional[str] = None
    uf_oab: Optional[str] = None
    tribunal: Optional[str] = None


class ValidateAllResponse(BaseModel):
    """Response com resultados de validação."""
    valid: bool
    errors: list
    fields: dict


from pydantic import BaseModel


@router.post("/validar-tudo", summary="Validar múltiplos campos")
@limiter.limit("30/minute")
def validar_tudo(request: ValidateAllRequest):
    """
    Valida múltiplos campos de uma vez.
    
    Retorna quais campos são válidos e quais têm erro.
    """
    errors = []
    fields = {}
    
    if request.numero_processo:
        result = validate_cnj(request.numero_processo)
        fields["numero_processo"] = result.to_dict()
        if not result.valid:
            errors.append("numero_processo")
    
    if request.numero_oab:
        result = validate_oab(request.numero_oab, request.uf_oab)
        fields["numero_oab"] = result.to_dict()
        if not result.valid:
            errors.append("numero_oab")
    
    if request.tribunal:
        result = validate_tribunal(request.tribunal)
        fields["tribunal"] = result.to_dict()
        if not result.valid:
            errors.append("tribunal")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "fields": fields,
    }