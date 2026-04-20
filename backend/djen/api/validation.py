"""
Validações para CAPTAÇÃO BLINDADA.

Validações de CNJ, OAB, Tribuais e outros campos.
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass

log = logging.getLogger("captacao.validation")


# =============================================================================
# Lista de Tribunais CNJ
# =============================================================================

TRIBUNAIS_CNJ = {
    # Justiça Federal
    "trf1": {"nome": "Tribunal Regional Federal 1ª Região", "tipo": "federal"},
    "trf2": {"nome": "Tribunal Regional Federal 2ª Região", "tipo": "federal"},
    "trf3": {"nome": "Tribunal Regional Federal 3ª Região", "tipo": "federal"},
    "trf4": {"nome": "Tribunal Regional Federal 4ª Região", "tipo": "federal"},
    "trf5": {"nome": "Tribunal Regional Federal 5ª Região", "tipo": "federal"},
    "trf6": {"nome": "Tribunal Regional Federal 6ª Região", "tipo": "federal"},
    
    # Justiça do Trabalho
    "tst": {"nome": "Tribunal Superior do Trabalho", "tipo": "trabalho"},
    "trt1": {"nome": "Tribunal Regional do Trabalho 1ª Região", "tipo": "trabalho"},
    "trt2": {"nome": "Tribunal Regional do Trabalho 2ª Região", "tipo": "trabalho"},
    "trt3": {"nome": "Tribunal Regional do Trabalho 3ª Região", "tipo": "trabalho"},
    "trt4": {"nome": "Tribunal Regional do Trabalho 4ª Região", "tipo": "trabalho"},
    "trt5": {"nome": "Tribunal Regional do Trabalho 5ª Região", "tipo": "trabalho"},
    "trt6": {"nome": "Tribunal Regional do Trabalho 6ª Região", "tipo": "trabalho"},
    "trt7": {"nome": "Tribunal Regional do Trabalho 7ª Região", "tipo": "trabalho"},
    "trt8": {"nome": "Tribunal Regional do Trabalho 8ª Região", "tipo": "trabalho"},
    "trt9": {"nome": "Tribunal Regional do Trabalho 9ª Região", "tipo": "trabalho"},
    "trt10": {"nome": "Tribunal Regional do Trabalho 10ª Região", "tipo": "trabalho"},
    "trt11": {"nome": "Tribunal Regional do Trabalho 11ª Região", "tipo": "trabalho"},
    "trt12": {"nome": "Tribunal Regional do Trabalho 12ª Região", "tipo": "trabalho"},
    "trt13": {"nome": "Tribunal Regional do Trabalho 13ª Região", "tipo": "trabalho"},
    "trt14": {"nome": "Tribunal Regional do Trabalho 14ª Região", "tipo": "trabalho"},
    "trt15": {"nome": "Tribunal Regional do Trabalho 15ª Região", "tipo": "trabalho"},
    "trt16": {"nome": "Tribunal Regional do Trabalho 16ª Região", "tipo": "trabalho"},
    "trt17": {"nome": "Tribunal Regional do Trabalho 17ª Região", "tipo": "trabalho"},
    "trt18": {"nome": "Tribunal Regional do Trabalho 18ª Região", "tipo": "trabalho"},
    "trt19": {"nome": "Tribunal Regional do Trabalho 19ª Região", "tipo": "trabalho"},
    "trt20": {"nome": "Tribunal Regional do Trabalho 20ª Região", "tipo": "trabalho"},
    "trt21": {"nome": "Tribunal Regional do Trabalho 21ª Região", "tipo": "trabalho"},
    "trt22": {"nome": "Tribunal Regional do Trabalho 22ª Região", "tipo": "trabalho"},
    "trt23": {"nome": "Tribunal Regional do Trabalho 23ª Região", "tipo": "trabalho"},
    
    # Justiça Estadual
    "tjsp": {"nome": "Tribunal de Justiça de São Paulo", "tipo": "estadual"},
    "tjrj": {"nome": "Tribunal de Justiça do Rio de Janeiro", "tipo": "estadual"},
    "tjmg": {"nome": "Tribunal de Justiça de Minas Gerais", "tipo": "estadual"},
    "tjrs": {"nome": "Tribunal de Justiça do Rio Grande do Sul", "tipo": "estadual"},
    "tjpr": {"nome": "Tribunal de Justiça do Paraná", "tipo": "estadual"},
    "tjsc": {"nome": "Tribunal de Justiça de Santa Catarina", "tipo": "estadual"},
    "tjba": {"nome": "Tribunal de Justiça da Bahia", "tipo": "estadual"},
    "tjpe": {"nome": "Tribunal de Justiça de Pernambuco", "tipo": "estadual"},
    "tjce": {"nome": "Tribunal de Justiça do Ceará", "tipo": "estadual"},
    "tjgo": {"nome": "Tribunal de Justiça de Goiás", "tipo": "estadual"},
    "tjpa": {"nome": "Tribunal de Justiça do Pará", "tipo": "estadual"},
    "tjma": {"nome": "Tribunal de Justiça do Maranhão", "tipo": "estadual"},
    "tjmt": {"nome": "Tribunal de Justiça de Mato Grosso", "tipo": "estadual"},
    "tjms": {"nome": "Tribunal de Justiça de Mato Grosso do Sul", "tipo": "estadual"},
    "tjal": {"nome": "Tribunal de Justiça de Alagoas", "tipo": "estadual"},
    "tjpb": {"nome": "Tribunal de Justiça da Paraíba", "tipo": "estadual"},
    "tjpi": {"nome": "Tribunal de Justiça do Piauí", "tipo": "estadual"},
    "tjam": {"nome": "Tribunal de Justiça do Amazonas", "tipo": "estadual"},
    "tjrn": {"nome": "Tribunal de Justiça do Rio Grande do Norte", "tipo": "estadual"},
    "tjse": {"nome": "Tribunal de Justiça de Sergipe", "tipo": "estadual"},
    "tjes": {"nome": "Tribunal de Justiça do Espírito Santo", "tipo": "estadual"},
    "tjro": {"nome": "Tribunal de Justiça de Rondônia", "tipo": "estadual"},
    "tjac": {"nome": "Tribunal de Justiça do Acre", "tipo": "estadual"},
    "tjap": {"nome": "Tribunal de Justiça do Amapá", "tipo": "estadual"},
    "tjrr": {"nome": "Tribunal de Justiça de Roraima", "tipo": "estadual"},
    "tjto": {"nome": "Tribunal de Justiça do Tocantins", "tipo": "estadual"},
    "tjdft": {"nome": "Tribunal de Justiça do Distrito Federal e Territórios", "tipo": "estadual"},
    
    # Superiores
    "stj": {"nome": "Superior Tribunal de Justiça", "tipo": "superior"},
    "stf": {"nome": "Supremo Tribunal Federal", "tipo": "superior"},
    "tse": {"nome": "Tribunal Superior Eleitoral", "tipo": "superior"},
    "stm": {"nome": "Tribunal Superior Militar", "tipo": "superior"},
    "casacivil": {"nome": "Casa Civil", "tipo": "especial"},
}


# =============================================================================
# Resultado de Validação
# =============================================================================

@dataclass
class ValidationResult:
    """Resultado de uma validação."""
    valid: bool
    field: str
    message: Optional[str] = None
    value: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }


# =============================================================================
# Validador de CNJ
# =============================================================================

class CNJValidator:
    """
    Valida número de processo CNJ.
    
    Formato: NNNNNNN-DD.YYYY.D.T.RO.AAAA
    Exemplo: 0000832-56.2018.8.10.0001
    """
    
    # Regex para formato completo CNJ
    CNJ_PATTERN = re.compile(
        r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$"
    )
    
    # Versão simples (sem pontos)
    CNJ_PATTERN_SIMPLE = re.compile(
        r"^\d{7}\d{2}\d{4}\d\d{2}\d{4}$"
    )
    
    @classmethod
    def validate(cls, numero: str) -> ValidationResult:
        """Valida número de processo CNJ."""
        if not numero:
            return ValidationResult(
                valid=False,
                field="numero_processo",
                message="Número é obrigatório",
                value=numero
            )
        
        # Remove espaços
        numero = numero.strip()
        
        # Tenta validar formato com pontos
        if cls.CNJ_PATTERN.match(numero):
            return ValidationResult(
                valid=True,
                field="numero_processo",
                value=numero
            )
        
        # Tenta válido simples (14 dígitos)
        numeros = re.sub(r"\D", "", numero)
        if len(numeros) == 20:
            # Formato: NNNNNNNDDYYYYDTRROAAA
            formatted = f"{numeros[:7]}-{numeros[7:9]}.{numeros[9:13]}.{numeros[13]}.{numeros[14:16]}.{numeros[16:]}"
            return ValidationResult(
                valid=True,
                field="numero_processo",
                message=f"Formato aceito: {formatted}",
                value=formatted
            )
        
        # Erro
        return ValidationResult(
            valid=False,
            field="numero_processo",
            message="Formato inválido. Use: NNNNNNN-DD.YYYY.D.T.RO.AAAA (ex: 0000832-56.2018.8.10.0001)",
            value=numero
        )


# =============================================================================
# Validador de OAB
# =============================================================================

class OABValidator:
    """
    Valida número de OAB.
    
    Formato: XX00000N-A
    Exemplo: SP123456A
    """
    
    OAB_PATTERN = re.compile(r"^[A-Z]{2}\d{6}[A-Z]?$")
    
    @classmethod
    def validate(cls, numero: str, uf: Optional[str] = None) -> ValidationResult:
        """Valida número de OAB."""
        if not numero:
            return ValidationResult(
                valid=False,
                field="numero_oab",
                message="Número OAB é obrigatório",
                value=numero
            )
        
        numero = numero.strip().upper()
        
        if cls.OAB_PATTERN.match(numero):
            return ValidationResult(
                valid=True,
                field="numero_oab",
                value=numero
            )
        
        # Tenta aceitar só números
        numeros = re.sub(r"\D", "", numero)
        if len(numeros) >= 6 and len(numeros) <= 7:
            # Formato aceito mas precisa da UF
            if uf:
                formatted = f"{uf.upper()}{numeros}"
                return ValidationResult(
                    valid=True,
                    field="numero_oab",
                    message="Formato aceito, adicione UF",
                    value=formatted
                )
            return ValidationResult(
                valid=False,
                field="numero_oab",
                message="Número OAB precisa de UF (ex: SP123456)",
                value=numero
            )
        
        return ValidationResult(
            valid=False,
            field="numero_oab",
            message="Formato inválido. Use: UF+numero (ex: SP123456)",
            value=numero
        )


# =============================================================================
# Validador de Tribunal
# =============================================================================

class TribunalValidator:
    """Valida tribunal contra lista conhecida."""
    
    @classmethod
    def validate(cls, tribunal: str) -> ValidationResult:
        """Valida tribunal."""
        if not tribunal:
            return ValidationResult(
                valid=False,
                field="tribunal",
                message="Tribunal é obrigatório",
                value=tribunal
            )
        
        tribunal_lower = tribunal.strip().lower()
        
        if tribunal_lower in TRIBUNAIS_CNJ:
            info = TRIBUNAIS_CNJ[tribunal_lower]
            return ValidationResult(
                valid=True,
                field="tribunal",
                value=tribunal_lower,
                message=info["nome"]
            )
        
        #Suggestions próximas
        suggestions = []
        for t in TRIBUNAIS_CNJ.keys():
            if t.startswith(tribunal_lower[:2]):
                suggestions.append(t)
        
        msg = f"Tribunal '{tribunal}' não encontrado"
        if suggestions:
            msg += f". Talvez você quis dizer: {', '.join(suggestions)}"
        
        return ValidationResult(
            valid=False,
            field="tribunal",
            message=msg,
            value=tribunal
        )


# =============================================================================
# Funções Auxiliares
# =============================================================================

def validate_cnj(numero: str) -> ValidationResult:
    """Valida CNJ."""
    return CNJValidator.validate(numero)


def validate_oab(numero: str, uf: Optional[str] = None) -> ValidationResult:
    """Valida OAB."""
    return OABValidator.validate(numero, uf)


def validate_tribunal(tribunal: str) -> ValidationResult:
    """Valida tribunal."""
    return TribunalValidator.validate(tribunal)


def get_tribunais(tipo: Optional[str] = None) -> list:
    """Retorna lista de tribunais, opcionalmente filtrados por tipo."""
    if tipo:
        return [
            {"sigla": k, "nome": v["nome"]}
            for k, v in TRIBUNAIS_CNJ.items()
            if v.get("tipo") == tipo
        ]
    return [
        {"sigla": k, "nome": v["nome"], "tipo": v.get("tipo")}
        for k, v in TRIBUNAIS_CNJ.items()
    ]


log.info("Validadores configurados: CNJ, OAB, Tribuais")