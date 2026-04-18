"""
DJen Sources - Modulos de coleta de publicacoes judiciais de fontes reais.
"""

from .datajud import DatajudSource
from .tjsp_dje import TJSPDjeSource
from .dejt import DEJTSource
from .querido_diario import QueridoDiarioSource
from .jusbrasil import JusBrasilSource

__all__ = [
    "DatajudSource",
    "TJSPDjeSource",
    "DEJTSource",
    "QueridoDiarioSource",
    "JusBrasilSource",
]
