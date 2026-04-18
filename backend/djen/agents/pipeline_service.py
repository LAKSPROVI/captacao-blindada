"""
Pipeline Service - Facade para o sistema multi-agentes.

Ponto de entrada unico para processar um numero de processo:
- Inicializa ProcessoCanonical
- Executa AgentOrchestrator
- Gerencia cache em memoria
- Emite eventos de progresso para WebSocket
"""

import logging
import os
import time
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from djen.agents.canonical_model import (
    AgentResult, AgentStatus, ProcessoCanonical,
    ProcessoResponse, ProcessoResumoResponse,
    TimelineResponse, RiscoResponse, PipelineStatusResponse,
    NivelRisco,
)
from djen.agents.orchestrator import AgentOrchestrator, AgentRegistry

# Importar agentes para que se registrem via @register_agent
import djen.agents.specialized  # noqa: F401
import djen.agents.ml_agents  # noqa: F401

log = logging.getLogger("captacao.pipeline")

# =========================================================================
# Configuracao de agentes ML
# =========================================================================

# Ativado via variavel de ambiente USE_ML_AGENTS=true|1|yes
_USE_ML_AGENTS = os.environ.get("USE_ML_AGENTS", "").lower() in ("true", "1", "yes")

if _USE_ML_AGENTS:
    log.info("USE_ML_AGENTS ativado - agentes ML serao preferidos quando disponiveis")


def _swap_ml_agents(agent_names: Optional[List[str]]) -> Optional[List[str]]:
    """
    Se USE_ML_AGENTS estiver ativado, substitui nomes de agentes
    heuristicos pelos equivalentes ML quando disponiveis no registry.

    Args:
        agent_names: Lista de nomes de agentes ou None (todos).

    Returns:
        Lista com nomes substituidos ou None.
    """
    if not _USE_ML_AGENTS or agent_names is None:
        return agent_names

    from djen.agents.ml_agents import ML_AGENT_MAP

    swapped = []
    for name in agent_names:
        ml_name = ML_AGENT_MAP.get(name)
        if ml_name and AgentRegistry.get(ml_name):
            log.debug("Swap: %s -> %s", name, ml_name)
            swapped.append(ml_name)
        else:
            swapped.append(name)
    return swapped


def _get_default_agents_with_ml() -> Optional[List[str]]:
    """
    Quando USE_ML_AGENTS esta ativo e agent_names e None (todos),
    retorna lista com agentes ML substituindo os heuristicos.
    Retorna None se ML nao esta ativo (usa todos do registry).
    """
    if not _USE_ML_AGENTS:
        return None

    from djen.agents.ml_agents import ML_AGENT_MAP

    registry = AgentRegistry.all()
    result = []
    ml_replacements = set(ML_AGENT_MAP.values())

    for name in registry:
        # Pular agentes heuristicos que tem substituto ML
        if name in ML_AGENT_MAP:
            ml_name = ML_AGENT_MAP[name]
            if ml_name in registry:
                continue  # Sera adicionado pela versao ML
        # Pular agentes ML se o heuristico correspondente nao esta na lista
        # (eles ja serao incluidos normalmente)
        result.append(name)

    return result

# Referencia lazy para ResultadoRepository (evita import circular)
_resultado_repo: Optional[Any] = None


def get_resultado_repo():
    """Obtem o ResultadoRepository singleton (lazy init)."""
    global _resultado_repo
    if _resultado_repo is None:
        from djen.api.app import get_database
        from djen.api.resultado_repository import ResultadoRepository
        _resultado_repo = ResultadoRepository(get_database())
    return _resultado_repo


# =========================================================================
# Cache em memoria
# =========================================================================

class ProcessoCache:
    """Cache thread-safe em memoria para processos ja analisados."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, numero: str) -> Optional[ProcessoCanonical]:
        with self._lock:
            entry = self._cache.get(numero)
            if entry is None:
                return None
            # Verificar TTL
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                del self._cache[numero]
                return None
            return entry["processo"]

    def set(self, numero: str, processo: ProcessoCanonical):
        with self._lock:
            # Evictar se cache cheio (LRU simples: remove mais antigo)
            if len(self._cache) >= self.max_size and numero not in self._cache:
                oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
                del self._cache[oldest_key]
            self._cache[numero] = {
                "processo": processo,
                "timestamp": time.time(),
            }

    def invalidate(self, numero: str):
        with self._lock:
            self._cache.pop(numero, None)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "keys": list(self._cache.keys()),
            }


# Instancia global do cache
_cache = ProcessoCache()


def get_cache() -> ProcessoCache:
    return _cache


# =========================================================================
# Pipeline Status tracking (para progresso em tempo real)
# =========================================================================

class PipelineTracker:
    """Rastreia status de pipelines em execucao para WebSocket."""

    def __init__(self):
        self._pipelines: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable]] = {}

    def start(self, numero: str):
        with self._lock:
            self._pipelines[numero] = {
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "progress": 0.0,
                "agents": [],
                "current_agent": None,
            }

    def update(self, numero: str, agent_name: str, status: str, progress: float):
        with self._lock:
            pipeline = self._pipelines.get(numero)
            if pipeline:
                pipeline["progress"] = progress
                pipeline["current_agent"] = agent_name
                pipeline["agents"].append({
                    "agent": agent_name,
                    "status": status,
                    "progress": progress,
                    "timestamp": datetime.now().isoformat(),
                })
        # Notificar subscribers
        self._notify(numero, {
            "type": "progress",
            "numero_processo": numero,
            "agent": agent_name,
            "status": status,
            "progress": progress,
        })

    def complete(self, numero: str, status: str = "completed"):
        with self._lock:
            pipeline = self._pipelines.get(numero)
            if pipeline:
                pipeline["status"] = status
                pipeline["progress"] = 100.0
                pipeline["completed_at"] = datetime.now().isoformat()
        self._notify(numero, {
            "type": "completed",
            "numero_processo": numero,
            "status": status,
            "progress": 100.0,
        })

    def get_status(self, numero: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._pipelines.get(numero)

    def subscribe(self, numero: str, callback: Callable):
        with self._lock:
            if numero not in self._subscribers:
                self._subscribers[numero] = []
            self._subscribers[numero].append(callback)

    def unsubscribe(self, numero: str, callback: Callable):
        with self._lock:
            subs = self._subscribers.get(numero, [])
            if callback in subs:
                subs.remove(callback)

    def _notify(self, numero: str, event: Dict[str, Any]):
        with self._lock:
            subs = list(self._subscribers.get(numero, []))
        for cb in subs:
            try:
                cb(event)
            except Exception:
                pass


# Instancia global do tracker
_tracker = PipelineTracker()


def get_tracker() -> PipelineTracker:
    return _tracker


# =========================================================================
# Pipeline Service
# =========================================================================

class PipelineService:
    """
    Facade principal para processar um processo judicial.

    Uso:
        service = PipelineService()
        processo = service.analisar("0044631-56.2012.8.10.0001")
    """

    def __init__(self, max_workers: int = 4, timeout: int = 120,
                 use_cache: bool = True):
        self.orchestrator = AgentOrchestrator(
            max_workers=max_workers,
            timeout=timeout,
        )
        self.use_cache = use_cache
        self.cache = get_cache()
        self.tracker = get_tracker()
        self._repo = None  # lazy init

    @property
    def repo(self):
        """ResultadoRepository com lazy init."""
        if self._repo is None:
            try:
                self._repo = get_resultado_repo()
            except Exception as e:
                log.warning("ResultadoRepository indisponivel: %s", e)
        return self._repo

    def analisar(self, numero_processo: str,
                 tribunal: Optional[str] = None,
                 agent_names: Optional[List[str]] = None,
                 force_refresh: bool = False) -> ProcessoCanonical:
        """
        Analisa um processo judicial executando o pipeline completo de agentes.

        Args:
            numero_processo: Numero do processo (CNJ)
            tribunal: Tribunal (opcional, detectado automaticamente)
            agent_names: Lista de agentes especificos (None = todos)
            force_refresh: Ignorar cache

        Returns:
            ProcessoCanonical enriquecido
        """
        # Normalizar numero
        numero_normalizado = numero_processo.strip()

        # Verificar cache L1 (memoria)
        if self.use_cache and not force_refresh:
            cached = self.cache.get(numero_normalizado)
            if cached:
                log.info("Cache L1 HIT para %s", numero_normalizado)
                return cached

            # Verificar cache L2 (SQLite)
            if self.repo:
                try:
                    db_cached = self.repo.obter(numero_normalizado)
                    if db_cached:
                        log.info("Cache L2 (DB) HIT para %s", numero_normalizado)
                        # Promover para L1
                        self.cache.set(numero_normalizado, db_cached)
                        return db_cached
                except Exception as e:
                    log.warning("Erro ao consultar L2 para %s: %s", numero_normalizado, e)

        log.info("Iniciando pipeline para %s", numero_normalizado)

        # Criar ProcessoCanonical inicial
        processo = ProcessoCanonical(
            numero_processo=numero_normalizado,
            tribunal=tribunal,
        )

        # Configurar tracker
        self.tracker.start(numero_normalizado)

        # Configurar callback de progresso
        def on_progress(agent_name: str, status: str, percent: float):
            self.tracker.update(numero_normalizado, agent_name, status, percent)

        self.orchestrator.set_progress_callback(on_progress)

        try:
            # Aplicar swap de agentes ML se configurado
            effective_agents = agent_names
            if _USE_ML_AGENTS:
                if effective_agents is not None:
                    effective_agents = _swap_ml_agents(effective_agents)
                else:
                    effective_agents = _get_default_agents_with_ml()

            # Executar pipeline
            processo = self.orchestrator.process(processo, effective_agents)
            self.tracker.complete(numero_normalizado, "completed")

            # Salvar no cache L1 (memoria)
            if self.use_cache:
                self.cache.set(numero_normalizado, processo)

            # Salvar no cache L2 (SQLite)
            if self.repo:
                try:
                    self.repo.salvar(processo)
                    log.info("Resultado persistido no DB para %s", numero_normalizado)
                except Exception as e:
                    log.warning("Erro ao persistir no DB para %s: %s", numero_normalizado, e)

        except Exception as e:
            log.error("Pipeline FALHOU para %s: %s", numero_normalizado, e)
            self.tracker.complete(numero_normalizado, "failed")
            raise

        return processo

    def get_resumo(self, processo: ProcessoCanonical) -> ProcessoResumoResponse:
        """Gera visao executiva resumida."""
        return ProcessoResumoResponse(
            numero_processo=processo.numero_formatado or processo.numero_processo,
            tribunal=processo.tribunal,
            classe_processual=processo.classe_processual,
            status=processo.status.value,
            fase=processo.fase.value,
            risco_geral=processo.risco_geral.value,
            risco_score=processo.risco_score,
            resumo_executivo=processo.resumo_executivo,
            pontos_atencao=processo.pontos_atencao,
            proximos_passos=processo.proximos_passos,
            prazo_mais_urgente=processo.prazo_mais_urgente,
            valor_causa=processo.valor_causa,
            total_partes=processo.total_partes,
            total_movimentacoes=processo.total_movimentacoes,
            total_comunicacoes=processo.total_comunicacoes,
            duracao_dias=processo.duracao_dias,
        )

    def get_timeline(self, processo: ProcessoCanonical) -> TimelineResponse:
        """Gera visao de timeline."""
        return TimelineResponse(
            numero_processo=processo.numero_formatado or processo.numero_processo,
            total_eventos=len(processo.timeline),
            timeline=processo.timeline,
        )

    def get_riscos(self, processo: ProcessoCanonical) -> RiscoResponse:
        """Gera visao de riscos."""
        recomendacoes = []
        for ind in processo.indicadores_risco:
            if ind.recomendacao:
                recomendacoes.append(ind.recomendacao)
        return RiscoResponse(
            numero_processo=processo.numero_formatado or processo.numero_processo,
            risco_geral=processo.risco_geral,
            risco_score=processo.risco_score,
            indicadores=processo.indicadores_risco,
            recomendacoes=recomendacoes,
        )

    def get_pipeline_status(self, numero_processo: str) -> Optional[PipelineStatusResponse]:
        """Retorna status do pipeline em execucao."""
        status = self.tracker.get_status(numero_processo)
        if not status:
            # Tentar no cache
            cached = self.cache.get(numero_processo)
            if cached:
                return PipelineStatusResponse(
                    numero_processo=numero_processo,
                    status="completed",
                    agents=cached.agents_executed,
                    progress_percent=100.0,
                    elapsed_ms=cached.processing_time_ms or 0,
                )
            return None

        return PipelineStatusResponse(
            numero_processo=numero_processo,
            status=status["status"],
            agents=[
                AgentResult(
                    agent_name=a["agent"],
                    status=AgentStatus(a["status"]) if a["status"] in AgentStatus.__members__ else AgentStatus.pending,
                )
                for a in status.get("agents", [])
            ],
            progress_percent=status.get("progress", 0),
            elapsed_ms=0,
        )

    @staticmethod
    def list_agents() -> List[Dict[str, str]]:
        """Lista todos os agentes registrados."""
        agents = []
        for name, cls in AgentRegistry.all().items():
            agents.append({
                "name": name,
                "description": cls.description,
                "depends_on": cls.depends_on,
                "priority": cls.priority,
            })
        return sorted(agents, key=lambda a: a["priority"])

    def listar_resultados(self, limit: int = 50, offset: int = 0,
                          tribunal: Optional[str] = None,
                          area: Optional[str] = None,
                          risco: Optional[str] = None) -> Dict[str, Any]:
        """Lista resultados persistidos no banco de dados."""
        if not self.repo:
            return {"total": 0, "limit": limit, "offset": offset, "resultados": []}
        return self.repo.listar(limit=limit, offset=offset,
                                tribunal=tribunal, area=area, risco=risco)


# Instancia singleton
_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    global _service
    if _service is None:
        _service = PipelineService()
    return _service
