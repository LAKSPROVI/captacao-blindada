"""
Sanitizacao de dados externos antes de inclusao em prompts LLM.

Previne ataques de prompt injection removendo padroes de instrucao,
caracteres de controle e limitando tamanho do texto.

Tambem fornece validacao de saida do LLM para garantir que respostas
estejam em formatos esperados antes de armazenamento.
"""

import re
from typing import Any, Dict, List, Optional, Set


# =========================================================================
# Input Sanitization (antes de enviar ao LLM)
# =========================================================================

_INJECTION_PATTERNS = [
    re.compile(p)
    for p in [
        r'(?i)ignore\s+(previous|above|all)\s+(instructions?|prompts?|context)',
        r'(?i)disregard\s+(previous|above|all)',
        r'(?i)forget\s+(everything|previous|above)',
        r'(?i)you\s+are\s+now',
        r'(?i)new\s+instructions?:',
        r'(?i)system\s*prompt:',
        r'(?i)assistant\s*:',
        r'(?i)human\s*:',
        r'(?i)<\s*/?system\s*>',
        r'(?i)\[INST\]',
        r'(?i)\[/INST\]',
        r'(?i)<<\s*SYS\s*>>',
        r'(?i)<<\s*/SYS\s*>>',
        r'(?i)\bdo\s+not\s+follow\b',
        r'(?i)\boverride\b.{0,20}\binstructions?\b',
    ]
]

_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_for_llm(text: str, max_length: int = 500) -> str:
    """
    Sanitiza texto externo antes de incluir em prompts LLM.

    - Remove padroes comuns de prompt injection
    - Remove caracteres de controle
    - Trunca ao comprimento maximo

    Args:
        text: Texto a sanitizar (pode vir de scraping, banco, etc.)
        max_length: Comprimento maximo permitido.

    Returns:
        Texto sanitizado.
    """
    if not text:
        return ""

    sanitized = str(text)

    for pattern in _INJECTION_PATTERNS:
        sanitized = pattern.sub('[FILTERED]', sanitized)

    sanitized = _CONTROL_CHARS_RE.sub('', sanitized)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized.strip()


# =========================================================================
# Output Validation (apos receber resposta do LLM)
# =========================================================================

_HTML_SCRIPT_RE = re.compile(r'<\s*/?(?:script|iframe|object|embed|form|input|style)[^>]*>', re.IGNORECASE)
_HTML_EVENT_RE = re.compile(r'\bon\w+\s*=', re.IGNORECASE)


def validate_area(area: str, allowed: Optional[Set[str]] = None) -> Optional[str]:
    """Valida area juridica contra valores permitidos."""
    if allowed is None:
        allowed = {
            "criminal", "trabalhista", "tributaria", "familia", "consumidor",
            "civel", "ambiental", "administrativo", "previdenciario", "empresarial",
        }
    area = (area or "").lower().strip()
    return area if area in allowed else None


def validate_fase(fase: str, allowed: Optional[Set[str]] = None) -> Optional[str]:
    """Valida fase processual contra valores permitidos."""
    if allowed is None:
        allowed = {
            "conhecimento", "recursal", "execucao", "cumprimento",
            "liquidacao", "cautelar", "desconhecida",
        }
    fase = (fase or "").lower().strip()
    return fase if fase in allowed else None


def validate_score(value: Any, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Valida e clampa score numerico dentro do intervalo permitido."""
    try:
        v = float(value)
    except (ValueError, TypeError):
        return (min_val + max_val) / 2  # valor padrao no meio do intervalo
    return max(min_val, min(max_val, v))


def validate_previsao(previsao: str) -> str:
    """Valida valor de previsao contra opcoes permitidas."""
    allowed = {"favoravel", "moderado", "desfavoravel"}
    previsao = (previsao or "").lower().strip()
    return previsao if previsao in allowed else "moderado"


def sanitize_llm_output_text(text: str, max_length: int = 2000) -> str:
    """
    Sanitiza texto de saida do LLM antes de armazenar.

    Remove tags HTML/script perigosas e trunca ao comprimento maximo.
    """
    if not text:
        return ""

    sanitized = str(text)

    # Remove tags HTML perigosas
    sanitized = _HTML_SCRIPT_RE.sub('', sanitized)
    # Remove event handlers inline
    sanitized = _HTML_EVENT_RE.sub('', sanitized)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized.strip()


def sanitize_string_list(items: Any, max_items: int = 10, max_item_length: int = 500) -> List[str]:
    """Sanitiza lista de strings vindas do LLM."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items[:max_items]:
        if isinstance(item, str):
            clean = sanitize_llm_output_text(item, max_length=max_item_length)
            if clean:
                result.append(clean)
    return result
