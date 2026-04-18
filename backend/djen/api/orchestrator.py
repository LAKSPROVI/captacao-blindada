"""
Framework Base de Agentes + Orquestrador Central.

Implementa o padrao de orchestration com:
- BaseAgent: classe abstrata para todos os agentes
- AgentOrchestrator: coordena execucao, dependencias e consolidacao
- Pipeline: define sequencia/paralelismo de agentes
- Cache e fallback inteligente
"""

import logging
import time
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Type

from djen.agents.canonical_model import (
    AgentResult, AgentStatus, ProcessoCanonical,
)

log = logging.getLogger("captacao.agents")


# =========================================================================
# Base Agent
# =========================================================================

class BaseAgent(ABC):
    """
    Classe base para todos os agentes especializados.
    Cada agente recebe o ProcessoCanonical, enriquece e retorna.
    """

    name: str = "base"
    description: str = ""
    depends_on: List[str] = []  # Agentes que devem rodar antes
    priority: int = 5  # 1=mais alta, 10=mais baixa

    def __init__(self):
        self.log = logging.getLogger(f"captacao.agents.{self.name}")

    @abstractmethod
    def execute(self, processo: ProcessoCanonical) -> ProcessoCanonical:
        """
        Executa o agente sobre o processo.
        Deve enriquecer e retornar o ProcessoCanonical.
        """
        pass

    def can_execute(self, processo: ProcessoCanonical) -> bool:
        """
        Verifica se o agente pode executar dado o estado atual.
        Override para validacoes especificas.
        """
        return True

    def _safe_execute(self, processo: ProcessoCanonical) -> AgentResult:
        """Executa com tratamento de erro e metricas."""
        started = datetime.now().isoformat()
        t0 = time.time()

        try:
            if not self.can_execute(processo):
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.skipped,
                    started_at=started,
                    completed_at=datetime.now().isoformat(),
                    duration_ms=0,
                )

            processo_updated = self.execute(processo)
            elapsed = int((time.time() - t0) * 1000)

            # Copiar campos atualizados de volta
            for field in processo_updated.__class__.model_fields:
                val = getattr(processo_updated, field)
                setattr(processo, field, val)

            self.log.info("[%s] Concluido em %dms", self.name, elapsed)
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.completed,
                started_at=started,
                completed_at=datetime.now().isoformat(),
                duration_ms=elapsed,
            )

        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            self.log.error("[%s] ERRO: %s", self.name, e)
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.failed,
                started_at=started,
                completed_at=datetime.now().isoformat(),
                duration_ms=elapsed,
                error=str(e),
            )


# =========================================================================
# Agent Registry
# =========================================================================

class AgentRegistry:
    """Registro central de agentes disponiveis."""

    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_class: Type[BaseAgent]):
        cls._agents[agent_class.name] = agent_class
        return agent_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseAgent]]:
        return cls._agents.get(name)

    @classmethod
    def all(cls) -> Dict[str, Type[BaseAgent]]:
        return dict(cls._agents)

    @classmethod
    def list_names(cls) -> List[str]:
        return list(cls._agents.keys())


def register_agent(cls):
    """Decorator para registrar agente automaticamente."""
    AgentRegistry.register(cls)
    return cls


# =========================================================================
# Orchestrator
# =========================================================================

class AgentOrchestrator:
    """
    Orquestrador central do sistema multi-agentes.

    Responsabilidades:
    - Planeja sequencia de execucao baseado em dependencias
    - Executa agentes em paralelo quando possivel
    - Gerencia fallback em caso de falha
    - Consolida resultado final no ProcessoCanonical
    - Emite eventos de progresso via callback
    """

    def __init__(self, max_workers: int = 4, timeout: int = 120):
        self.max_workers = max_workers
        self.timeout = timeout
        self.log = logging.getLogger("captacao.orchestrator")
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """Define callback para progresso: callback(agent_name, status, percent)"""
        self._progress_callback = callback

    def _emit_progress(self, agent_name: str, status: str, percent: float):
        if self._progress_callback:
            try:
                self._progress_callback(agent_name, status, percent)
            except Exception:
                pass

    def _resolve_execution_order(self, agents: List[BaseAgent]) -> List[List[BaseAgent]]:
        """
        Resolve dependencias e agrupa agentes em camadas de execucao.
        Agentes na mesma camada podem rodar em paralelo.
        Retorna lista de camadas: [[agentes_paralelos], [agentes_paralelos], ...]
        """
        agent_map = {a.name: a for a in agents}
        resolved: List[List[BaseAgent]] = []
        executed: Set[str] = set()
        remaining = list(agents)

        max_iterations = len(agents) + 1
        for _ in range(max_iterations):
            if not remaining:
                break

            # Encontrar agentes cujas dependencias ja foram satisfeitas
            layer = []
            still_remaining = []

            for agent in remaining:
                deps = set(agent.depends_on)
                if deps.issubset(executed):
                    layer.append(agent)
                else:
                    still_remaining.append(agent)

            if not layer:
                # Dependencia circular ou impossivel - forcar execucao
                self.log.warning("Dependencias nao resolvidas, forcando: %s",
                                 [a.name for a in still_remaining])
                layer = still_remaining
                still_remaining = []

            # Ordenar camada por prioridade
            layer.sort(key=lambda a: a.priority)
            resolved.append(layer)
            executed.update(a.name for a in layer)
            remaining = still_remaining

        return resolved

    def process(self, processo: ProcessoCanonical,
                agent_names: Optional[List[str]] = None) -> ProcessoCanonical:
        """
        Executa pipeline completo de agentes sobre um processo.

        Args:
            processo: ProcessoCanonical com dados iniciais
            agent_names: Lista de agentes para executar (None = todos)

        Returns:
            ProcessoCanonical enriquecido
        """
        t0 = time.time()
        self.log.info("="*60)
        self.log.info("PIPELINE: Processo %s", processo.numero_processo)
        self.log.info("="*60)

        # Instanciar agentes
        registry = AgentRegistry.all()
        if agent_names:
            agents = [registry[n]() for n in agent_names if n in registry]
        else:
            agents = [cls() for cls in registry.values()]

        if not agents:
            self.log.warning("Nenhum agente disponivel")
            return processo

        # Resolver ordem de execucao
        layers = self._resolve_execution_order(agents)
        total_agents = len(agents)
        completed_count = 0

        self.log.info("Pipeline: %d agentes em %d camadas", total_agents, len(layers))
        for i, layer in enumerate(layers):
            self.log.info("  Camada %d: %s", i+1, [a.name for a in layer])

        # Executar camada por camada
        for layer_idx, layer in enumerate(layers):
            layer_names = [a.name for a in layer]
            self.log.info("--- Camada %d/%d: %s ---", layer_idx+1, len(layers), layer_names)

            if len(layer) == 1:
                # Execucao sequencial (1 agente)
                agent = layer[0]
                self._emit_progress(agent.name, "running", completed_count/total_agents*100)
                result = agent._safe_execute(processo)
                processo.agents_executed.append(result)
                completed_count += 1
                self._emit_progress(agent.name, result.status.value, completed_count/total_agents*100)
            else:
                # Execucao paralela
                with ThreadPoolExecutor(max_workers=min(len(layer), self.max_workers)) as executor:
                    futures = {}
                    for agent in layer:
                        self._emit_progress(agent.name, "running", completed_count/total_agents*100)
                        futures[executor.submit(agent._safe_execute, processo)] = agent

                    for future in as_completed(futures, timeout=self.timeout):
                        agent = futures[future]
                        try:
                            result = future.result()
                            processo.agents_executed.append(result)
                        except Exception as e:
                            processo.agents_executed.append(AgentResult(
                                agent_name=agent.name,
                                status=AgentStatus.failed,
                                error=str(e),
                            ))
                        completed_count += 1
                        self._emit_progress(agent.name, "completed", completed_count/total_agents*100)

        # Finalizar
        elapsed = int((time.time() - t0) * 1000)
        processo.processing_time_ms = elapsed
        processo.enriched_at = datetime.now().isoformat()

        # Stats
        completed = sum(1 for r in processo.agents_executed if r.status == AgentStatus.completed)
        failed = sum(1 for r in processo.agents_executed if r.status == AgentStatus.failed)
        skipped = sum(1 for r in processo.agents_executed if r.status == AgentStatus.skipped)

        self.log.info("="*60)
        self.log.info("PIPELINE COMPLETO: %dms", elapsed)
        self.log.info("  Sucesso: %d | Falha: %d | Ignorado: %d", completed, failed, skipped)
        self.log.info("="*60)

        self._emit_progress("pipeline", "completed", 100)
        return processo
