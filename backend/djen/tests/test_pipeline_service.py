"""
Tests for djen.agents.pipeline_service - ProcessoCache, PipelineTracker, PipelineService.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from djen.agents.canonical_model import (
    AgentResult,
    AgentStatus,
    EventoTimeline,
    IndicadorRisco,
    NivelRisco,
    ProcessoCanonical,
)
from djen.agents.pipeline_service import (
    PipelineService,
    PipelineTracker,
    ProcessoCache,
)


# =========================================================================
# Helpers
# =========================================================================

def _make_processo(numero: str = "0001234-56.2020.8.10.0001", **kwargs) -> ProcessoCanonical:
    return ProcessoCanonical(numero_processo=numero, **kwargs)


# =========================================================================
# ProcessoCache tests
# =========================================================================


class TestProcessoCache:
    def test_cache_starts_empty(self):
        cache = ProcessoCache()
        stats = cache.stats()
        assert stats["size"] == 0
        assert stats["keys"] == []

    def test_set_and_get(self):
        cache = ProcessoCache()
        p = _make_processo()
        cache.set(p.numero_processo, p)
        result = cache.get(p.numero_processo)
        assert result is not None
        assert result.numero_processo == p.numero_processo

    def test_get_returns_none_for_missing(self):
        cache = ProcessoCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = ProcessoCache(ttl_seconds=0)
        p = _make_processo()
        cache.set(p.numero_processo, p)
        # ttl_seconds=0 means any elapsed time > 0 expires it
        time.sleep(0.01)
        assert cache.get(p.numero_processo) is None

    def test_lru_eviction(self):
        cache = ProcessoCache(max_size=2)
        p1 = _make_processo("001")
        p2 = _make_processo("002")
        p3 = _make_processo("003")

        cache.set("001", p1)
        time.sleep(0.01)
        cache.set("002", p2)
        time.sleep(0.01)
        # Cache is full (2). Adding p3 should evict the oldest (001).
        cache.set("003", p3)

        assert cache.get("001") is None
        assert cache.get("002") is not None
        assert cache.get("003") is not None

    def test_invalidate(self):
        cache = ProcessoCache()
        p = _make_processo()
        cache.set(p.numero_processo, p)
        cache.invalidate(p.numero_processo)
        assert cache.get(p.numero_processo) is None

    def test_clear(self):
        cache = ProcessoCache()
        for i in range(5):
            cache.set(str(i), _make_processo(str(i)))
        assert cache.stats()["size"] == 5
        cache.clear()
        assert cache.stats()["size"] == 0

    def test_stats(self):
        cache = ProcessoCache(max_size=50, ttl_seconds=7200)
        cache.set("a", _make_processo("a"))
        cache.set("b", _make_processo("b"))
        stats = cache.stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 50
        assert stats["ttl_seconds"] == 7200
        assert set(stats["keys"]) == {"a", "b"}

    def test_thread_safety(self):
        cache = ProcessoCache(max_size=200)
        errors = []

        def writer(start: int):
            try:
                for i in range(50):
                    key = str(start + i)
                    cache.set(key, _make_processo(key))
            except Exception as e:
                errors.append(e)

        def reader(start: int):
            try:
                for i in range(50):
                    cache.get(str(start + i))
            except Exception as e:
                errors.append(e)

        threads = []
        for s in range(0, 200, 50):
            threads.append(threading.Thread(target=writer, args=(s,)))
            threads.append(threading.Thread(target=reader, args=(s,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # All 200 items should be in cache (max_size=200)
        assert cache.stats()["size"] == 200


# =========================================================================
# PipelineTracker tests
# =========================================================================


class TestPipelineTracker:
    def test_start_creates_entry(self):
        tracker = PipelineTracker()
        tracker.start("001")
        status = tracker.get_status("001")
        assert status is not None
        assert status["status"] == "running"
        assert status["progress"] == 0.0

    def test_update_changes_progress(self):
        tracker = PipelineTracker()
        tracker.start("001")
        tracker.update("001", "agent_a", "running", 50.0)
        status = tracker.get_status("001")
        assert status["progress"] == 50.0
        assert status["current_agent"] == "agent_a"
        assert len(status["agents"]) == 1

    def test_complete_sets_status(self):
        tracker = PipelineTracker()
        tracker.start("001")
        tracker.complete("001", "completed")
        status = tracker.get_status("001")
        assert status["status"] == "completed"
        assert status["progress"] == 100.0
        assert "completed_at" in status

    def test_get_status_returns_none_for_unknown(self):
        tracker = PipelineTracker()
        assert tracker.get_status("unknown") is None

    def test_subscribe_receives_events(self):
        tracker = PipelineTracker()
        tracker.start("001")
        events = []
        tracker.subscribe("001", lambda e: events.append(e))
        tracker.update("001", "agent_x", "running", 25.0)
        assert len(events) == 1
        assert events[0]["type"] == "progress"
        assert events[0]["agent"] == "agent_x"

    def test_unsubscribe_stops_events(self):
        tracker = PipelineTracker()
        tracker.start("001")
        events = []
        cb = lambda e: events.append(e)  # noqa: E731
        tracker.subscribe("001", cb)
        tracker.update("001", "a1", "running", 10.0)
        assert len(events) == 1
        tracker.unsubscribe("001", cb)
        tracker.update("001", "a2", "running", 20.0)
        assert len(events) == 1  # no new event

    def test_multiple_subscribers(self):
        tracker = PipelineTracker()
        tracker.start("001")
        events_a = []
        events_b = []
        tracker.subscribe("001", lambda e: events_a.append(e))
        tracker.subscribe("001", lambda e: events_b.append(e))
        tracker.update("001", "agent_z", "running", 30.0)
        assert len(events_a) == 1
        assert len(events_b) == 1


# =========================================================================
# PipelineService tests
# =========================================================================


class TestPipelineService:
    @pytest.fixture(autouse=True)
    def _setup(self):
        """Patch orchestrator and repo to avoid side effects."""
        with patch("djen.agents.pipeline_service.get_cache") as mock_cache_fn, \
             patch("djen.agents.pipeline_service.get_tracker") as mock_tracker_fn:
            self.mock_cache = ProcessoCache()
            self.mock_tracker = PipelineTracker()
            mock_cache_fn.return_value = self.mock_cache
            mock_tracker_fn.return_value = self.mock_tracker

            # Build service with mocked orchestrator
            service = PipelineService.__new__(PipelineService)
            service.orchestrator = MagicMock()
            service.use_cache = True
            service.cache = self.mock_cache
            service.tracker = self.mock_tracker
            service._repo = None
            self.service = service
            yield

    def test_list_agents(self):
        agents = PipelineService.list_agents()
        # Should return a list (may be empty if no agents registered in test env)
        assert isinstance(agents, list)
        # Each entry should have expected keys if non-empty
        for a in agents:
            assert "name" in a
            assert "description" in a
            assert "priority" in a

    def test_get_resumo(self):
        p = _make_processo(
            tribunal="TJMA",
            classe_processual="Acao Civil",
            resumo_executivo="Teste resumo",
        )
        resumo = self.service.get_resumo(p)
        assert resumo.numero_processo == p.numero_processo
        assert resumo.tribunal == "TJMA"
        assert resumo.classe_processual == "Acao Civil"
        assert resumo.resumo_executivo == "Teste resumo"
        assert resumo.status == "desconhecido"
        assert resumo.fase == "desconhecida"

    def test_get_timeline(self):
        eventos = [
            EventoTimeline(data="2024-01-01", titulo="Distribuicao", tipo="distribuicao"),
            EventoTimeline(data="2024-02-01", titulo="Despacho", tipo="despacho"),
        ]
        p = _make_processo(timeline=eventos)
        tl = self.service.get_timeline(p)
        assert tl.numero_processo == p.numero_processo
        assert tl.total_eventos == 2
        assert len(tl.timeline) == 2

    def test_get_riscos(self):
        indicadores = [
            IndicadorRisco(
                categoria="prazo",
                nivel=NivelRisco.alto,
                score=0.8,
                descricao="Prazo critico",
                recomendacao="Verificar prazo",
            ),
            IndicadorRisco(
                categoria="merito",
                nivel=NivelRisco.baixo,
                score=0.2,
                descricao="Merito OK",
                recomendacao=None,
            ),
        ]
        p = _make_processo(
            risco_geral=NivelRisco.alto,
            risco_score=0.8,
            indicadores_risco=indicadores,
        )
        riscos = self.service.get_riscos(p)
        assert riscos.risco_geral == NivelRisco.alto
        assert riscos.risco_score == 0.8
        assert len(riscos.indicadores) == 2
        # Only indicators with recomendacao should appear in recomendacoes
        assert riscos.recomendacoes == ["Verificar prazo"]

    def test_get_pipeline_status_unknown(self):
        result = self.service.get_pipeline_status("nonexistent")
        assert result is None

    def test_get_pipeline_status_cached(self):
        p = _make_processo("cached-001")
        p.agents_executed = [
            AgentResult(agent_name="a1", status=AgentStatus.completed),
        ]
        p.processing_time_ms = 500
        self.mock_cache.set("cached-001", p)
        result = self.service.get_pipeline_status("cached-001")
        assert result is not None
        assert result.status == "completed"
        assert result.progress_percent == 100.0
        assert result.elapsed_ms == 500
