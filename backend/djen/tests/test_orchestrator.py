"""
Tests for djen.agents.orchestrator module.

Covers BaseAgent, AgentRegistry, register_agent decorator,
_safe_execute, AgentOrchestrator dependency resolution and process execution.
"""

import pytest
import time
from unittest.mock import MagicMock

from djen.agents.canonical_model import (
    AgentResult, AgentStatus, ProcessoCanonical,
)
from djen.agents.orchestrator import (
    BaseAgent, AgentRegistry, AgentOrchestrator, register_agent,
)


# =========================================================================
# Helpers – save/restore registry state between tests
# =========================================================================

@pytest.fixture(autouse=True)
def clean_registry():
    """Backup and restore AgentRegistry._agents around every test."""
    backup = dict(AgentRegistry._agents)
    AgentRegistry._agents.clear()
    yield
    AgentRegistry._agents.clear()
    AgentRegistry._agents.update(backup)


def _make_processo(**kwargs) -> ProcessoCanonical:
    return ProcessoCanonical(numero_processo="0000000-00.0000.0.00.0000", **kwargs)


# =========================================================================
# Concrete test agents (never import real specialised agents)
# =========================================================================

class AlphaAgent(BaseAgent):
    name = "alpha"
    description = "Test agent alpha"
    depends_on = []
    priority = 1

    def execute(self, processo):
        processo.resumo_executivo = "alpha enriched"
        return processo


class BetaAgent(BaseAgent):
    name = "beta"
    description = "Test agent beta"
    depends_on = ["alpha"]
    priority = 2

    def execute(self, processo):
        processo.resumo_situacao_atual = "beta enriched"
        return processo


class GammaAgent(BaseAgent):
    name = "gamma"
    description = "Test agent gamma"
    depends_on = []
    priority = 3

    def execute(self, processo):
        processo.pontos_atencao = ["gamma point"]
        return processo


class FailingAgent(BaseAgent):
    name = "failing"
    description = "Agent that always raises"
    depends_on = []
    priority = 5

    def execute(self, processo):
        raise RuntimeError("boom")


class SkippableAgent(BaseAgent):
    name = "skippable"
    description = "Agent that skips"
    depends_on = []
    priority = 5

    def can_execute(self, processo):
        return False

    def execute(self, processo):
        return processo


# =========================================================================
# 1-2. BaseAgent is abstract / concrete can be instantiated
# =========================================================================

class TestBaseAgent:
    def test_base_agent_is_abstract(self):
        with pytest.raises(TypeError):
            BaseAgent()

    def test_concrete_agent_instantiates(self):
        agent = AlphaAgent()
        assert agent.name == "alpha"


# =========================================================================
# 3-6. AgentRegistry basics
# =========================================================================

class TestAgentRegistry:
    def test_register_adds_agent(self):
        AgentRegistry.register(AlphaAgent)
        assert "alpha" in AgentRegistry._agents

    def test_get_returns_correct_class(self):
        AgentRegistry.register(AlphaAgent)
        assert AgentRegistry.get("alpha") is AlphaAgent

    def test_get_returns_none_for_unknown(self):
        assert AgentRegistry.get("nonexistent") is None

    def test_all_returns_all_registered(self):
        AgentRegistry.register(AlphaAgent)
        AgentRegistry.register(BetaAgent)
        all_agents = AgentRegistry.all()
        assert set(all_agents.keys()) == {"alpha", "beta"}

    def test_list_names(self):
        AgentRegistry.register(AlphaAgent)
        AgentRegistry.register(GammaAgent)
        names = AgentRegistry.list_names()
        assert set(names) == {"alpha", "gamma"}


# =========================================================================
# 7. @register_agent decorator
# =========================================================================

class TestRegisterDecorator:
    def test_decorator_registers(self):
        @register_agent
        class DeltaAgent(BaseAgent):
            name = "delta"
            description = "decorated"
            depends_on = []
            priority = 5

            def execute(self, processo):
                return processo

        assert AgentRegistry.get("delta") is DeltaAgent


# =========================================================================
# 8-10. _safe_execute
# =========================================================================

class TestSafeExecute:
    def test_completed_on_success(self):
        agent = AlphaAgent()
        processo = _make_processo()
        result = agent._safe_execute(processo)
        assert result.status == AgentStatus.completed
        assert result.agent_name == "alpha"
        assert result.error is None

    def test_failed_on_exception(self):
        agent = FailingAgent()
        processo = _make_processo()
        result = agent._safe_execute(processo)
        assert result.status == AgentStatus.failed
        assert "boom" in result.error

    def test_skipped_when_cannot_execute(self):
        agent = SkippableAgent()
        processo = _make_processo()
        result = agent._safe_execute(processo)
        assert result.status == AgentStatus.skipped

    def test_duration_tracked(self):
        agent = AlphaAgent()
        processo = _make_processo()
        result = agent._safe_execute(processo)
        assert result.duration_ms is not None
        assert result.duration_ms >= 0
        assert result.started_at is not None
        assert result.completed_at is not None


# =========================================================================
# 11-14. _resolve_execution_order
# =========================================================================

class TestResolveExecutionOrder:
    def setup_method(self):
        self.orch = AgentOrchestrator()

    def test_no_deps_first_layer(self):
        agents = [AlphaAgent(), GammaAgent()]
        layers = self.orch._resolve_execution_order(agents)
        assert len(layers) == 1
        names = {a.name for a in layers[0]}
        assert names == {"alpha", "gamma"}

    def test_dependent_agent_later_layer(self):
        agents = [AlphaAgent(), BetaAgent()]
        layers = self.orch._resolve_execution_order(agents)
        assert len(layers) == 2
        assert layers[0][0].name == "alpha"
        assert layers[1][0].name == "beta"

    def test_parallel_agents_same_layer(self):
        agents = [AlphaAgent(), GammaAgent()]
        layers = self.orch._resolve_execution_order(agents)
        assert len(layers) == 1
        assert len(layers[0]) == 2

    def test_complex_dependency_graph(self):
        """alpha,gamma -> layer 0;  beta (depends alpha) -> layer 1"""
        agents = [BetaAgent(), AlphaAgent(), GammaAgent()]
        layers = self.orch._resolve_execution_order(agents)
        layer0_names = {a.name for a in layers[0]}
        assert "alpha" in layer0_names
        assert "gamma" in layer0_names
        assert any(a.name == "beta" for layer in layers[1:] for a in layer)

    def test_circular_dependency_forced(self):
        """Circular deps should still complete (forced into a layer)."""

        class CycleA(BaseAgent):
            name = "cycle_a"
            depends_on = ["cycle_b"]
            priority = 1
            def execute(self, p):
                return p

        class CycleB(BaseAgent):
            name = "cycle_b"
            depends_on = ["cycle_a"]
            priority = 1
            def execute(self, p):
                return p

        agents = [CycleA(), CycleB()]
        layers = self.orch._resolve_execution_order(agents)
        all_names = {a.name for layer in layers for a in layer}
        assert all_names == {"cycle_a", "cycle_b"}

    def test_sorted_by_priority_within_layer(self):
        agents = [GammaAgent(), AlphaAgent()]  # gamma=3, alpha=1
        layers = self.orch._resolve_execution_order(agents)
        assert layers[0][0].name == "alpha"  # lower priority number first


# =========================================================================
# 15-19. AgentOrchestrator.process
# =========================================================================

class TestOrchestratorProcess:
    def setup_method(self):
        self.orch = AgentOrchestrator(max_workers=2, timeout=30)

    def test_process_executes_all_agents(self):
        AgentRegistry.register(AlphaAgent)
        AgentRegistry.register(GammaAgent)
        processo = _make_processo()
        result = self.orch.process(processo)
        executed_names = {r.agent_name for r in result.agents_executed}
        assert executed_names == {"alpha", "gamma"}

    def test_process_respects_agent_names_filter(self):
        AgentRegistry.register(AlphaAgent)
        AgentRegistry.register(GammaAgent)
        processo = _make_processo()
        result = self.orch.process(processo, agent_names=["alpha"])
        executed_names = {r.agent_name for r in result.agents_executed}
        assert executed_names == {"alpha"}
        assert "gamma" not in executed_names

    def test_progress_callback_called(self):
        AgentRegistry.register(AlphaAgent)
        callback = MagicMock()
        self.orch.set_progress_callback(callback)
        processo = _make_processo()
        self.orch.process(processo)
        assert callback.call_count >= 2  # at least running + completed
        # final call should be pipeline completed at 100%
        last_call = callback.call_args_list[-1]
        assert last_call[0][0] == "pipeline"
        assert last_call[0][1] == "completed"
        assert last_call[0][2] == 100

    def test_duration_tracked_in_result(self):
        AgentRegistry.register(AlphaAgent)
        processo = _make_processo()
        result = self.orch.process(processo)
        agent_result = result.agents_executed[0]
        assert agent_result.duration_ms is not None
        assert agent_result.duration_ms >= 0

    def test_processo_enriched_after_process(self):
        AgentRegistry.register(AlphaAgent)
        processo = _make_processo()
        result = self.orch.process(processo)
        assert result.enriched_at is not None
        assert result.processing_time_ms is not None
        assert result.processing_time_ms >= 0
        assert result.resumo_executivo == "alpha enriched"

    def test_process_with_no_agents_returns_processo(self):
        processo = _make_processo()
        result = self.orch.process(processo)
        assert result.numero_processo == processo.numero_processo
        assert len(result.agents_executed) == 0

    def test_process_handles_failing_agent(self):
        AgentRegistry.register(FailingAgent)
        processo = _make_processo()
        result = self.orch.process(processo)
        assert len(result.agents_executed) == 1
        assert result.agents_executed[0].status == AgentStatus.failed

    def test_process_with_dependencies(self):
        AgentRegistry.register(AlphaAgent)
        AgentRegistry.register(BetaAgent)
        processo = _make_processo()
        result = self.orch.process(processo)
        executed_names = [r.agent_name for r in result.agents_executed]
        assert "alpha" in executed_names
        assert "beta" in executed_names
        # alpha should execute before beta
        assert executed_names.index("alpha") < executed_names.index("beta")
        assert result.resumo_executivo == "alpha enriched"
        assert result.resumo_situacao_atual == "beta enriched"
