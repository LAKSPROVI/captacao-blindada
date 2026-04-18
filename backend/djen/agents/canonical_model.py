"""
Modelo de Dados Canonico - Sistema Multi-Agentes Juridico.

Modelo unificado que integra todas as informacoes enriquecidas
de um processo judicial, mantendo o numero do processo como
identificador unico.
"""

from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =========================================================================
# Enums
# =========================================================================

class StatusProcesso(str, Enum):
    ativo = "ativo"
    suspenso = "suspenso"
    arquivado = "arquivado"
    baixado = "baixado"
    extinto = "extinto"
    desconhecido = "desconhecido"


class NivelRisco(str, Enum):
    muito_baixo = "muito_baixo"
    baixo = "baixo"
    medio = "medio"
    alto = "alto"
    critico = "critico"


class PoloProcessual(str, Enum):
    ativo = "ativo"
    passivo = "passivo"
    terceiro = "terceiro"
    interessado = "interessado"
    ministerio_publico = "ministerio_publico"
    desconhecido = "desconhecido"


class TipoParte(str, Enum):
    pessoa_fisica = "pessoa_fisica"
    pessoa_juridica = "pessoa_juridica"
    ente_publico = "ente_publico"
    desconhecido = "desconhecido"


class FaseProcessual(str, Enum):
    conhecimento = "conhecimento"
    recursal = "recursal"
    execucao = "execucao"
    cumprimento = "cumprimento"
    liquidacao = "liquidacao"
    cautelar = "cautelar"
    desconhecida = "desconhecida"


class AgentStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


# =========================================================================
# Sub-modelos
# =========================================================================

class Advogado(BaseModel):
    nome: str
    oab: Optional[str] = None
    uf_oab: Optional[str] = None
    polo: Optional[PoloProcessual] = None


class ParteProcessual(BaseModel):
    nome: str
    tipo: TipoParte = TipoParte.desconhecido
    polo: PoloProcessual = PoloProcessual.desconhecido
    cpf_cnpj: Optional[str] = None
    advogados: List[Advogado] = []


class Movimentacao(BaseModel):
    codigo: Optional[int] = None
    nome: str
    data: str
    complemento: Optional[str] = None
    tipo: Optional[str] = None  # despacho, decisao, sentenca, etc


class Comunicacao(BaseModel):
    id: Optional[int] = None
    tipo: str  # Intimacao, Citacao, Edital
    data_disponibilizacao: str
    texto: Optional[str] = None
    meio: Optional[str] = None
    orgao: Optional[str] = None
    destinatarios: List[str] = []
    advogados_destinatarios: List[Advogado] = []


class ValorPecuniario(BaseModel):
    tipo: str  # causa, condenacao, acordo, honorarios, custas
    valor: float
    moeda: str = "BRL"
    data_referencia: Optional[str] = None
    descricao: Optional[str] = None


class Prazo(BaseModel):
    tipo: str  # recurso, manifestacao, cumprimento, etc
    data_inicio: Optional[str] = None
    data_fim: str
    dias_restantes: Optional[int] = None
    util: bool = True  # dias uteis
    descricao: Optional[str] = None
    urgente: bool = False


class EventoTimeline(BaseModel):
    data: str
    titulo: str
    descricao: Optional[str] = None
    tipo: str  # distribuicao, despacho, decisao, sentenca, recurso, etc
    relevancia: int = Field(default=5, ge=1, le=10)
    agente_origem: Optional[str] = None


class IndicadorRisco(BaseModel):
    categoria: str  # prazo, merito, procedimental, financeiro
    nivel: NivelRisco
    score: float = Field(ge=0.0, le=1.0)
    descricao: str
    recomendacao: Optional[str] = None


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    data: Dict[str, Any] = {}


# =========================================================================
# Modelo Canonico Principal
# =========================================================================

class ProcessoCanonical(BaseModel):
    """
    Modelo canonico unificado de um processo judicial.
    Integra dados de DataJud, DJEN e analise multi-agente.
    """

    # --- Identificacao ---
    numero_processo: str = Field(..., description="Numero unico CNJ")
    numero_formatado: Optional[str] = None
    tribunal: Optional[str] = None
    grau: Optional[str] = None  # G1, G2, JE, SUP
    justica: Optional[str] = None  # estadual, federal, trabalho, eleitoral, militar

    # --- Classificacao ---
    classe_processual: Optional[str] = None
    classe_codigo: Optional[int] = None
    assuntos: List[str] = []
    assuntos_codigos: List[int] = []
    area: Optional[str] = None  # civel, criminal, trabalhista, etc
    fase: FaseProcessual = FaseProcessual.desconhecida
    status: StatusProcesso = StatusProcesso.desconhecido

    # --- Orgao ---
    orgao_julgador: Optional[str] = None
    orgao_codigo: Optional[int] = None
    comarca: Optional[str] = None
    uf: Optional[str] = None
    municipio_ibge: Optional[int] = None

    # --- Datas ---
    data_ajuizamento: Optional[str] = None
    data_ultima_movimentacao: Optional[str] = None
    data_distribuicao: Optional[str] = None
    data_sentenca: Optional[str] = None
    data_transito_julgado: Optional[str] = None
    duracao_dias: Optional[int] = None

    # --- Partes ---
    partes: List[ParteProcessual] = []
    advogados: List[Advogado] = []
    total_partes: int = 0

    # --- Movimentacoes ---
    movimentacoes: List[Movimentacao] = []
    total_movimentacoes: int = 0
    ultima_movimentacao: Optional[Movimentacao] = None

    # --- Comunicacoes (DJEN) ---
    comunicacoes: List[Comunicacao] = []
    total_comunicacoes: int = 0

    # --- Valores ---
    valores: List[ValorPecuniario] = []
    valor_causa: Optional[float] = None

    # --- Prazos ---
    prazos: List[Prazo] = []
    prazo_mais_urgente: Optional[Prazo] = None

    # --- Timeline ---
    timeline: List[EventoTimeline] = []

    # --- Risco ---
    risco_geral: NivelRisco = NivelRisco.medio
    risco_score: float = Field(default=0.5, ge=0.0, le=1.0)
    indicadores_risco: List[IndicadorRisco] = []

    # --- Resumo ---
    resumo_executivo: Optional[str] = None
    resumo_situacao_atual: Optional[str] = None
    pontos_atencao: List[str] = []
    proximos_passos: List[str] = []

    # --- Meta ---
    formato_origem: Optional[str] = None  # Eletronico, Fisico
    sistema_origem: Optional[str] = None  # PJe, SAJ, PROJUDI, etc
    nivel_sigilo: int = 0
    fontes_consultadas: List[str] = []
    agents_executed: List[AgentResult] = []
    enriched_at: Optional[str] = None
    processing_time_ms: Optional[int] = None

    # --- Raw data ---
    raw_datajud: Optional[Dict[str, Any]] = None
    raw_djen: Optional[List[Dict[str, Any]]] = None


# =========================================================================
# Response Models
# =========================================================================

class ProcessoResponse(BaseModel):
    status: str = "success"
    processo: ProcessoCanonical
    visao: str = "completa"  # completa, executiva, timeline, risco
    tempo_processamento_ms: int = 0


class ProcessoResumoResponse(BaseModel):
    """Visao executiva resumida."""
    numero_processo: str
    tribunal: Optional[str]
    classe_processual: Optional[str]
    status: str
    fase: str
    risco_geral: str
    risco_score: float
    resumo_executivo: Optional[str]
    pontos_atencao: List[str]
    proximos_passos: List[str]
    prazo_mais_urgente: Optional[Prazo]
    valor_causa: Optional[float]
    total_partes: int
    total_movimentacoes: int
    total_comunicacoes: int
    duracao_dias: Optional[int]


class TimelineResponse(BaseModel):
    numero_processo: str
    total_eventos: int
    timeline: List[EventoTimeline]


class RiscoResponse(BaseModel):
    numero_processo: str
    risco_geral: NivelRisco
    risco_score: float
    indicadores: List[IndicadorRisco]
    recomendacoes: List[str]


class PipelineStatusResponse(BaseModel):
    numero_processo: str
    status: str  # running, completed, failed
    agents: List[AgentResult]
    progress_percent: float
    elapsed_ms: int
