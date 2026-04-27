"""
Captacao Peticao Blindada - Schemas Pydantic.
Modelos de request/response para a API REST.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator
import re as _re


# =========================================================================
# Enums
# =========================================================================

class FonteBusca(str, Enum):
    datajud = "datajud"
    djen_api = "djen_api"
    tjsp_dje = "tjsp_dje"
    dejt = "dejt"
    querido_diario = "querido_diario"
    jusbrasil = "jusbrasil"
    todas = "todas"


class TipoMonitorado(str, Enum):
    oab = "oab"
    processo = "processo"
    nome = "nome"
    parte = "parte"
    advogado = "advogado"


class TipoComunicacao(str, Enum):
    citacao = "C"
    intimacao = "I"
    edital = "E"


# =========================================================================
# Validators Reutilizaveis
# =========================================================================

_DATE_YYYY_MM_DD = _re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_DD_MM_YYYY = _re.compile(r"^\d{2}/\d{2}/\d{4}$")
_TIME_HH_MM = _re.compile(r"^\d{2}:\d{2}$")
_VALID_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

def _validate_date_str(v: str, field_name: str) -> str:
    """Valida formato de data YYYY-MM-DD ou DD/MM/AAAA."""
    if v is None:
        return v
    if not (_DATE_YYYY_MM_DD.match(v) or _DATE_DD_MM_YYYY.match(v)):
        raise ValueError(f"{field_name}: formato invalido. Use YYYY-MM-DD ou DD/MM/AAAA")
    return v

def _validate_time_str(v: str, field_name: str) -> str:
    """Valida formato de horario HH:MM."""
    if v is None:
        return v
    if not _TIME_HH_MM.match(v):
        raise ValueError(f"{field_name}: formato invalido. Use HH:MM")
    parts = v.split(":")
    h, m = int(parts[0]), int(parts[1])
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise ValueError(f"{field_name}: horario fora do intervalo valido (00:00-23:59)")
    return v

def _validate_dias_semana(v: str) -> str:
    """Valida dias da semana (1-7 separados por virgula)."""
    if v is None:
        return v
    for d in v.split(","):
        d = d.strip()
        if d not in {"1", "2", "3", "4", "5", "6", "7"}:
            raise ValueError(f"dias_semana: valor '{d}' invalido. Use 1-7 (1=seg, 7=dom)")
    return v

def _validate_uf(v: str) -> str:
    """Valida UF brasileira."""
    if v is None:
        return v
    if v.upper() not in _VALID_UFS:
        raise ValueError(f"UF '{v}' invalida")
    return v.upper()


class StatusMonitorado(str, Enum):
    ativo = "ativo"
    inativo = "inativo"


class TipoBusca(str, Enum):
    processo = "processo"
    oab = "oab"
    nome_parte = "nome_parte"
    nome_advogado = "nome_advogado"
    classe = "classe"
    assunto = "assunto"
    tribunal_geral = "tribunal_geral"
    todas = "todas"


class PrioridadeCaptacao(str, Enum):
    baixa = "baixa"
    normal = "normal"
    alta = "alta"
    urgente = "urgente"


# =========================================================================
# Request Models
# =========================================================================

class BuscaDatajudRequest(BaseModel):
    """Busca no DataJud (metadados processuais)."""
    tribunal: str = Field(..., description="Sigla do tribunal (ex: tjsp, stj, trf1)", json_schema_extra={"example": "tjsp"})
    numero_processo: Optional[str] = Field(None, description="Numero do processo sem formatacao", json_schema_extra={"example": "00008323520184013202"})
    classe_codigo: Optional[int] = Field(None, description="Codigo da classe processual", json_schema_extra={"example": 1116})
    assunto_codigo: Optional[int] = Field(None, description="Codigo do assunto", json_schema_extra={"example": 6177})
    orgao_julgador_codigo: Optional[int] = Field(None, description="Codigo do orgao julgador")
    data_inicio: Optional[str] = Field(None, description="Data inicio YYYY-MM-DD", json_schema_extra={"example": "2024-01-01"})
    data_fim: Optional[str] = Field(None, description="Data fim YYYY-MM-DD", json_schema_extra={"example": "2024-12-31"})
    tamanho: int = Field(10, ge=1, le=100, description="Quantidade de resultados")

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def validate_dates(cls, v):
        return _validate_date_str(v, "data") if v else v


class BuscaDjenRequest(BaseModel):
    """Busca no DJEN (comunicacoes processuais - texto completo)."""
    numero_processo: Optional[str] = Field(None, description="Numero do processo CNJ", json_schema_extra={"example": "0044631-56.2012.8.10.0001"})
    tribunal: Optional[str] = Field(None, description="Sigla do tribunal", json_schema_extra={"example": "TJMA"})
    numero_oab: Optional[str] = Field(None, description="Numero da OAB", json_schema_extra={"example": "123456"})
    uf_oab: Optional[str] = Field(None, description="UF da OAB", json_schema_extra={"example": "SP"})
    nome_advogado: Optional[str] = Field(None, description="Nome do advogado")
    nome_parte: Optional[str] = Field(None, description="Nome da parte")
    data_inicio: Optional[str] = Field(None, description="Data inicio DD/MM/AAAA", json_schema_extra={"example": "01/01/2024"})
    data_fim: Optional[str] = Field(None, description="Data fim DD/MM/AAAA", json_schema_extra={"example": "31/12/2024"})
    orgao_id: Optional[int] = Field(None, description="ID do orgao julgador")
    meio: Optional[str] = Field(None, description="D=Diario Eletronico, E=Edital")
    pagina: int = Field(0, ge=0, description="Pagina (0-indexed)")
    itens_por_pagina: int = Field(20, ge=1, le=100, description="Itens por pagina")


class BuscaUnificadaRequest(BaseModel):
    """Busca unificada em todas as fontes."""
    termo: str = Field(..., description="Termo de busca (processo, OAB, nome)", json_schema_extra={"example": "0044631-56.2012.8.10.0001"})
    fontes: List[FonteBusca] = Field(default=[FonteBusca.datajud, FonteBusca.djen_api], description="Fontes para buscar")
    tribunal: Optional[str] = Field(None, description="Filtrar por tribunal")
    data_inicio: Optional[str] = Field(None, description="Data inicio DD/MM/AAAA")
    data_fim: Optional[str] = Field(None, description="Data fim DD/MM/AAAA")
    max_resultados: int = Field(20, ge=1, le=200, description="Maximo de resultados por fonte")


class MonitoradoCreateRequest(BaseModel):
    """Criar novo monitorado."""
    tipo: TipoMonitorado = Field(..., description="Tipo de monitoramento")
    valor: str = Field(..., description="Valor a monitorar (OAB, processo, nome)", json_schema_extra={"example": "123456/SP"})
    nome_amigavel: Optional[str] = Field(None, description="Nome amigavel para identificacao")
    tribunal: Optional[str] = Field(None, description="Restringir a um tribunal")
    fontes: List[FonteBusca] = Field(default=[FonteBusca.datajud, FonteBusca.djen_api])
    # Agendamento
    intervalo_minutos: int = Field(120, ge=15, le=10080, description="Intervalo entre buscas automaticas (minutos)")
    horario_inicio: str = Field("06:00", description="Nao buscar antes deste horario (HH:MM)")
    horario_fim: str = Field("23:00", description="Nao buscar depois deste horario (HH:MM)")
    dias_semana: str = Field("1,2,3,4,5", description="Dias permitidos para busca (1=seg..7=dom)")

    @field_validator("horario_inicio", "horario_fim", mode="before")
    @classmethod
    def validate_horarios(cls, v):
        return _validate_time_str(v, "horario") if v else v

    @field_validator("dias_semana", mode="before")
    @classmethod
    def validate_dias(cls, v):
        return _validate_dias_semana(v) if v else v


class MonitoradoUpdateRequest(BaseModel):
    """Atualizar monitorado."""
    nome_amigavel: Optional[str] = None
    ativo: Optional[bool] = None
    tribunal: Optional[str] = None
    fontes: Optional[List[FonteBusca]] = None
    # Agendamento
    intervalo_minutos: Optional[int] = Field(None, ge=15, le=10080)
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_semana: Optional[str] = None


# =========================================================================
# Response Models
# =========================================================================

class PublicacaoResponse(BaseModel):
    """Publicacao judicial encontrada."""
    id: Optional[int] = None
    hash: Optional[str] = None
    fonte: str
    tribunal: str
    data_publicacao: str
    conteudo: str
    numero_processo: Optional[str] = None
    classe_processual: Optional[str] = None
    orgao_julgador: Optional[str] = None
    assuntos: List[str] = []
    movimentos: List[Dict[str, Any]] = []
    url_origem: Optional[str] = None
    caderno: Optional[str] = None
    pagina: Optional[str] = None
    oab_encontradas: List[str] = []
    advogados: List[str] = []
    partes: List[str] = []


class BuscaResponse(BaseModel):
    """Resultado de uma busca."""
    status: str = "success"
    fonte: str
    total: int
    tempo_ms: int
    resultados: List[PublicacaoResponse]
    erro: Optional[str] = None


class BuscaUnificadaResponse(BaseModel):
    """Resultado de busca unificada."""
    status: str = "success"
    total_geral: int
    tempo_total_ms: int
    resultados_por_fonte: Dict[str, BuscaResponse]


class MonitoradoResponse(BaseModel):
    """Monitorado cadastrado."""
    id: int
    tipo: str
    valor: str
    nome_amigavel: Optional[str] = None
    ativo: bool
    tribunal: Optional[str] = None
    fontes: str
    criado_em: Optional[str] = None
    ultima_busca: Optional[str] = None
    total_publicacoes: int = 0
    # Agendamento
    intervalo_minutos: int = 120
    horario_inicio: str = "06:00"
    horario_fim: str = "23:00"
    dias_semana: str = "1,2,3,4,5"
    proxima_busca: Optional[str] = None


class HealthSourceResponse(BaseModel):
    """Status de uma fonte."""
    source: str
    status: str
    message: Optional[str] = None
    latency_ms: Optional[int] = None
    proxy_used: Optional[bool] = None


class HealthResponse(BaseModel):
    """Health check geral."""
    status: str
    version: str
    uptime_seconds: int
    fontes: List[HealthSourceResponse]
    database: str
    scheduler: str


class StatsResponse(BaseModel):
    """Estatisticas do sistema."""
    total_monitorados: int
    monitorados_ativos: int
    total_publicacoes: int
    publicacoes_hoje: int
    publicacoes_semana: int
    total_buscas: int
    fontes_ativas: int
    ultima_busca: Optional[str] = None


class APIInfoResponse(BaseModel):
    """Informacoes da API."""
    nome: str = "Captacao Peticao Blindada"
    versao: str = "1.0.0"
    descricao: str = "API de monitoramento e busca de publicacoes judiciais"
    fontes_disponiveis: List[str]
    docs_url: str = "/docs"
    health_url: str = "/api/health"


class ModalidadeCaptacao(str, Enum):
    recorrente = "recorrente"
    faixa_fixa = "faixa_fixa"


# =========================================================================
# Captacao Automatizada - Request Models
# =========================================================================

class CaptacaoCreateRequest(BaseModel):
    """Criar nova captacao automatizada."""
    nome: str = Field(..., min_length=1, max_length=200, description="Nome identificador da captacao")
    descricao: Optional[str] = Field(None, description="Descricao/notas livres")
    tipo_busca: TipoBusca = Field(..., description="Tipo de busca a realizar")
    modalidade: ModalidadeCaptacao = Field(ModalidadeCaptacao.recorrente, description="recorrente ou faixa_fixa")

    # Parametros de busca (conforme tipo_busca)
    numero_processo: Optional[str] = Field(None, description="Numero CNJ (tipo_busca=processo)")
    numero_oab: Optional[str] = Field(None, description="Numero OAB (tipo_busca=oab)")
    uf_oab: Optional[str] = Field(None, description="UF da OAB (tipo_busca=oab)")
    nome_parte: Optional[str] = Field(None, description="Nome da parte (tipo_busca=nome_parte)")
    nome_advogado: Optional[str] = Field(None, description="Nome do advogado (tipo_busca=nome_advogado)")
    tribunal: Optional[str] = Field(None, description="Tribunal (sigla, ex: TJSP, stj)")
    tribunais: Optional[str] = Field(None, description="Lista de tribunais separados por virgula (ex: TJSP,TJRJ,TRF3)")
    classe_codigo: Optional[int] = Field(None, description="Codigo da classe processual CNJ (tipo_busca=classe)")
    assunto_codigo: Optional[int] = Field(None, description="Codigo do assunto CNJ (tipo_busca=assunto)")
    orgao_id: Optional[int] = Field(None, description="ID do orgao julgador (DJEN)")
    tipo_comunicacao: Optional[TipoComunicacao] = Field(None, description="I=intimacao, C=citacao, E=edital, NULL=todos")
    data_inicio: Optional[str] = Field(None, description="Data inicio (YYYY-MM-DD ou DD/MM/AAAA)")
    data_fim: Optional[str] = Field(None, description="Data fim (NULL=hoje)")

    # Fontes
    fontes: List[FonteBusca] = Field(
        ...,
        min_length=1,
        description="Pelo menos uma fonte deve ser selecionada",
    )

    # Scheduler
    intervalo_minutos: int = Field(120, ge=15, le=10080, description="Intervalo entre execucoes (15min a 7 dias)")
    horario_inicio: str = Field("06:00", description="Nao executar antes deste horario (HH:MM)")
    horario_fim: str = Field("23:00", description="Nao executar depois deste horario (HH:MM)")
    dias_semana: str = Field("1,2,3,4,5", description="Dias permitidos (1=seg..7=dom)")

    # Enriquecimento
    auto_enriquecer: bool = Field(False, description="Executar pipeline multi-agentes automaticamente")

    # Notificacao
    notificar_whatsapp: bool = Field(False, description="Enviar notificacao WhatsApp")
    notificar_email: bool = Field(False, description="Enviar notificacao email")
    prioridade: PrioridadeCaptacao = Field(PrioridadeCaptacao.normal, description="Prioridade de execucao")

    @field_validator("horario_inicio", "horario_fim", mode="before")
    @classmethod
    def validate_horarios(cls, v):
        return _validate_time_str(v, "horario") if v else v

    @field_validator("dias_semana", mode="before")
    @classmethod
    def validate_dias(cls, v):
        return _validate_dias_semana(v) if v else v

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def validate_dates(cls, v):
        return _validate_date_str(v, "data") if v else v

    @field_validator("uf_oab", mode="before")
    @classmethod
    def validate_uf(cls, v):
        return _validate_uf(v) if v else v


class CaptacaoUpdateRequest(BaseModel):
    """Atualizar captacao existente."""
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = None
    ativo: Optional[bool] = None
    modalidade: Optional[ModalidadeCaptacao] = None
    numero_processo: Optional[str] = None
    numero_oab: Optional[str] = None
    uf_oab: Optional[str] = None
    nome_parte: Optional[str] = None
    nome_advogado: Optional[str] = None
    tribunal: Optional[str] = None
    tribunais: Optional[str] = None
    classe_codigo: Optional[int] = None
    assunto_codigo: Optional[int] = None
    orgao_id: Optional[int] = None
    tipo_comunicacao: Optional[TipoComunicacao] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    fontes: Optional[List[FonteBusca]] = None
    intervalo_minutos: Optional[int] = Field(None, ge=15, le=10080)
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None
    dias_semana: Optional[str] = None
    auto_enriquecer: Optional[bool] = None
    notificar_whatsapp: Optional[bool] = None
    notificar_email: Optional[bool] = None
    prioridade: Optional[PrioridadeCaptacao] = None


class CaptacaoPreviewRequest(BaseModel):
    """Preview de captacao (dry-run, sem salvar)."""
    tipo_busca: TipoBusca = Field(..., description="Tipo de busca")
    numero_processo: Optional[str] = None
    numero_oab: Optional[str] = None
    uf_oab: Optional[str] = None
    nome_parte: Optional[str] = None
    nome_advogado: Optional[str] = None
    tribunal: Optional[str] = None
    tribunais: Optional[str] = None
    classe_codigo: Optional[int] = None
    assunto_codigo: Optional[int] = None
    orgao_id: Optional[int] = None
    tipo_comunicacao: Optional[TipoComunicacao] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    fontes: List[FonteBusca] = Field(default=[FonteBusca.datajud, FonteBusca.djen_api])


# =========================================================================
# Captacao Automatizada - Response Models
# =========================================================================

class CaptacaoResponse(BaseModel):
    """Captacao automatizada cadastrada."""
    id: int
    nome: str
    descricao: Optional[str] = None
    ativo: bool
    tipo_busca: str
    numero_processo: Optional[str] = None
    numero_oab: Optional[str] = None
    uf_oab: Optional[str] = None
    nome_parte: Optional[str] = None
    nome_advogado: Optional[str] = None
    tribunal: Optional[str] = None
    tribunais: Optional[str] = None
    classe_codigo: Optional[int] = None
    assunto_codigo: Optional[int] = None
    orgao_id: Optional[int] = None
    tipo_comunicacao: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    fontes: str
    intervalo_minutos: int
    horario_inicio: str
    horario_fim: str
    dias_semana: str
    proxima_execucao: Optional[str] = None
    pausado: bool = False
    auto_enriquecer: bool = False
    notificar_whatsapp: bool = False
    notificar_email: bool = False
    prioridade: str = "normal"
    criado_em: Optional[str] = None
    atualizado_em: Optional[str] = None
    ultima_execucao: Optional[str] = None
    total_execucoes: int = 0
    total_resultados: int = 0
    total_novos: int = 0


class ExecucaoCaptacaoResponse(BaseModel):
    """Execucao de captacao."""
    id: int
    captacao_id: int
    inicio: str
    fim: Optional[str] = None
    status: str
    fonte: str
    parametros_json: Optional[str] = None
    total_resultados: int = 0
    novos_resultados: int = 0
    duracao_ms: Optional[int] = None
    erro: Optional[str] = None
    criado_em: Optional[str] = None


class CaptacaoExecucaoResult(BaseModel):
    """Resultado de uma execucao de captacao."""
    captacao_id: int
    status: str
    fontes_consultadas: List[str]
    total_resultados: int = 0
    novos_resultados: int = 0
    tempo_total_ms: int = 0
    execucoes: List[ExecucaoCaptacaoResponse] = []
    processos_enriquecidos: List[str] = []
    erro: Optional[str] = None


class DiffResponse(BaseModel):
    """Resultado de comparacao entre execucoes."""
    captacao_id: int
    execucao_atual_id: Optional[int] = None
    execucao_anterior_id: Optional[int] = None
    novos: List[PublicacaoResponse] = []
    total_novos: int = 0
    total_mantidos: int = 0
    total_atual: int = 0
    resumo: str = ""


class CaptacaoStatsResponse(BaseModel):
    """Estatisticas de captacao."""
    total_captacoes: int = 0
    captacoes_ativas: int = 0
    captacoes_pausadas: int = 0
    total_execucoes: int = 0
    execucoes_hoje: int = 0
    total_novos_encontrados: int = 0
    ultima_execucao: Optional[str] = None
    por_tipo: Dict[str, int] = {}
# =========================================================================
# Multi-Tenant, Usuários e Tarifação - Request/Response Models
# =========================================================================

class TenantResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
    saldo_tokens: int
    criado_em: Optional[str] = None
    atualizado_em: Optional[str] = None

class TenantCreateRequest(BaseModel):
    nome: str = Field(..., min_length=2)
    ativo: bool = True
    saldo_tokens: int = Field(0, ge=0)

class TenantUpdateRequest(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None
    saldo_tokens: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    username: str
    full_name: str
    role: str
    criado_em: Optional[str] = None

class UserCreateRequest(BaseModel):
    tenant_id: Optional[int] = None
    username: str
    password: str = Field(..., min_length=8, description="Senha com minimo 8 caracteres")
    full_name: str
    role: Optional[str] = Field("editor", pattern=r"^(master|admin|editor|viewer)$", description="Papel do usuario")

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    tenant_id: Optional[int] = None

class FunctionCostResponse(BaseModel):
    function_name: str
    description: Optional[str] = None
    cost_tokens: int

class FunctionCostUpdateRequest(BaseModel):
    description: Optional[str] = None
    cost_tokens: Optional[int] = None

class UsageLogResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    function_name: str
    tokens_used: int
    metadata: Optional[str] = None
    data_uso: str

class BillingStatsResponse(BaseModel):
    tenant_id: int
    saldo_atual: int
    total_gasto_mes: int
    gasto_por_funcao: Dict[str, int]
