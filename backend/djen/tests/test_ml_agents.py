"""
Tests for djen/agents/ml_agents.py — ML/NLP agents with LLM integration.

All LLM calls are mocked; no real API requests are made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from djen.agents.canonical_model import (
    FaseProcessual,
    IndicadorRisco,
    NivelRisco,
    ProcessoCanonical,
    StatusProcesso,
)
from djen.agents.ml_agents import (
    ML_AGENT_MAP,
    AnalisadorJurisprudenciaML,
    ClassificadorCausaML,
    GeradorResumoML,
    LLMClient,
    PrevisorResultadoML,
    _build_process_context,
    _parse_json_response,
    get_llm_client,
)
from djen.agents.orchestrator import AgentRegistry
from djen.agents.specialized import (
    AnalisadorJurisprudencia,
    ClassificadorCausa,
    GeradorResumo,
    PrevisorResultado,
)


# =========================================================================
# Helpers
# =========================================================================

def _make_processo(**overrides) -> ProcessoCanonical:
    """Create a minimal ProcessoCanonical for testing."""
    defaults = dict(
        numero_processo="0000001-00.2024.8.26.0100",
        numero_formatado="0000001-00.2024.8.26.0100",
        tribunal="TJSP",
        classe_processual="Procedimento Comum Civel",
        area="civel",
        fase=FaseProcessual.conhecimento,
        status=StatusProcesso.ativo,
        assuntos=["Indenizacao por Dano Moral"],
    )
    defaults.update(overrides)
    return ProcessoCanonical(**defaults)


def _mock_openai_response(content: str) -> MagicMock:
    """Build a mock requests.Response mimicking OpenAI chat completion."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    return resp


# =========================================================================
# 1-4  LLMClient core
# =========================================================================

class TestLLMClient:

    def test_init_with_api_key(self):
        """1. LLMClient initialization with explicit API key."""
        client = LLMClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        assert client.available is True

    def test_init_without_api_key(self):
        """1b. LLMClient initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove env var if present
            import os
            old = os.environ.pop("GAMERON_API_KEY", None)
            try:
                client = LLMClient(api_key=None)
                assert client.api_key is None or client.api_key == ""
                assert client.available is False
            finally:
                if old is not None:
                    os.environ["GAMERON_API_KEY"] = old

    def test_chat_returns_none_without_api_key(self):
        """2. Chat returns None when API key is missing."""
        client = LLMClient(api_key=None)
        # Force api_key to None in case env has one
        client.api_key = None
        result = client.chat("system", "user")
        assert result is None

    @patch("djen.agents.ml_agents.requests.post")
    def test_chat_returns_none_on_network_error(self, mock_post):
        """3. Chat returns None on network error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("fail")
        client = LLMClient(api_key="key")
        result = client.chat("system", "user")
        assert result is None

    @patch("djen.agents.ml_agents.requests.post")
    def test_chat_returns_response_on_success(self, mock_post):
        """4. Chat returns response text on success."""
        mock_post.return_value = _mock_openai_response("Hello from LLM")
        client = LLMClient(api_key="key")
        result = client.chat("system", "user")
        assert result == "Hello from LLM"
        mock_post.assert_called_once()


# =========================================================================
# 5-7  _parse_json_response
# =========================================================================

class TestParseJsonResponse:

    def test_clean_json_string(self):
        """5. Extracts JSON from clean string."""
        raw = '{"area": "civel", "fase": "conhecimento"}'
        result = _parse_json_response(raw)
        assert result == {"area": "civel", "fase": "conhecimento"}

    def test_json_in_markdown_code_fence(self):
        """6. Extracts JSON from markdown code fences."""
        raw = 'Here is the result:\n```json\n{"area": "criminal"}\n```'
        result = _parse_json_response(raw)
        assert result == {"area": "criminal"}

    def test_invalid_json_returns_none(self):
        """7. Returns None on invalid JSON."""
        result = _parse_json_response("this is not json at all")
        assert result is None

    def test_none_input(self):
        result = _parse_json_response(None)
        assert result is None

    def test_empty_string(self):
        result = _parse_json_response("")
        assert result is None


# =========================================================================
# 8  _build_process_context
# =========================================================================

class TestBuildProcessContext:

    def test_returns_formatted_string(self):
        """8. _build_process_context returns formatted string."""
        p = _make_processo(valor_causa=15000.0, grau="G1")
        ctx = _build_process_context(p)
        assert "TJSP" in ctx
        assert "Procedimento Comum Civel" in ctx
        assert "Indenizacao por Dano Moral" in ctx
        assert "15,000.00" in ctx or "15000" in ctx
        assert "G1" in ctx


# =========================================================================
# 9-12  ClassificadorCausaML
# =========================================================================

class TestClassificadorCausaML:

    def _make_agent(self, use_llm=True):
        agent = ClassificadorCausaML()
        agent.use_llm = use_llm
        return agent

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_fallback_when_use_llm_false(self, mock_get_llm):
        """9. Falls back to heuristic when use_llm=False."""
        agent = self._make_agent(use_llm=False)
        p = _make_processo(area=None, fase=FaseProcessual.desconhecida)
        result = agent.execute(p)
        assert isinstance(result, ProcessoCanonical)
        mock_get_llm.assert_not_called()

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_fallback_when_llm_unavailable(self, mock_get_llm):
        """10. Falls back to heuristic when LLM returns None."""
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = None
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo(area=None)
        result = agent.execute(p)
        assert isinstance(result, ProcessoCanonical)

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_successful_classification(self, mock_get_llm):
        """11. Successfully classifies when LLM returns valid JSON."""
        llm_response = json.dumps({
            "area": "trabalhista",
            "fase": "recursal",
            "justificativa": "Trata-se de reclamacao trabalhista em grau recursal.",
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo(area=None, fase=FaseProcessual.desconhecida)
        result = agent.execute(p)
        assert result.area == "trabalhista"
        assert result.fase == FaseProcessual.recursal

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_handles_invalid_llm_response(self, mock_get_llm):
        """12. Handles invalid LLM response gracefully (bad area)."""
        llm_response = json.dumps({
            "area": "espacial_intergalatico",  # invalid
            "fase": "conhecimento",
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo(area="civel")
        result = agent.execute(p)
        # Area should remain unchanged because LLM returned invalid area
        assert result.area == "civel"
        assert result.fase == FaseProcessual.conhecimento


# =========================================================================
# 13-15  PrevisorResultadoML
# =========================================================================

class TestPrevisorResultadoML:

    def _make_agent(self, use_llm=True):
        agent = PrevisorResultadoML()
        agent.use_llm = use_llm
        return agent

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_fallback_when_llm_unavailable(self, mock_get_llm):
        """13. Falls back to heuristic when LLM unavailable."""
        mock_client = MagicMock()
        mock_client.available = False
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)
        assert isinstance(result, ProcessoCanonical)

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_successful_prediction(self, mock_get_llm):
        """14. Successfully predicts when LLM returns valid JSON."""
        llm_response = json.dumps({
            "previsao": "favoravel",
            "confianca": 0.85,
            "fundamentacao": "Jurisprudencia consolidada a favor.",
            "fatores_positivos": ["Sumula aplicavel", "Provas robustas"],
            "fatores_negativos": ["Processo demorado"],
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)

        # Should have added risk indicator
        previsao_indicators = [
            i for i in result.indicadores_risco
            if i.categoria == "previsao_resultado"
        ]
        assert len(previsao_indicators) == 1
        ind = previsao_indicators[0]
        assert ind.nivel == NivelRisco.baixo
        assert "[PREVISAO ML]" in result.pontos_atencao[-1]

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_handles_missing_fields(self, mock_get_llm):
        """15. Handles missing fields in LLM response."""
        llm_response = json.dumps({
            "previsao": "moderado",
            # confianca, fundamentacao, fatores omitted
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)

        previsao_indicators = [
            i for i in result.indicadores_risco
            if i.categoria == "previsao_resultado"
        ]
        assert len(previsao_indicators) == 1
        assert previsao_indicators[0].nivel == NivelRisco.medio


# =========================================================================
# 16-18  GeradorResumoML
# =========================================================================

class TestGeradorResumoML:

    def _make_agent(self, use_llm=True):
        agent = GeradorResumoML()
        agent.use_llm = use_llm
        return agent

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_fallback_when_llm_unavailable(self, mock_get_llm):
        """16. Falls back to heuristic when LLM unavailable."""
        mock_client = MagicMock()
        mock_client.available = False
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)
        assert isinstance(result, ProcessoCanonical)

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_successful_summary_generation(self, mock_get_llm):
        """17. Successfully generates summary from LLM response."""
        llm_response = json.dumps({
            "resumo_executivo": "Processo civel de indenizacao em fase de conhecimento.",
            "situacao_atual": "Aguardando audiencia de conciliacao.",
            "pontos_atencao": ["Prazo para contestacao proximo", "Valor elevado"],
            "proximos_passos": ["Preparar contestacao", "Reunir provas"],
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)

        assert result.resumo_executivo == "Processo civel de indenizacao em fase de conhecimento."
        assert result.resumo_situacao_atual == "Aguardando audiencia de conciliacao."
        assert any("[ML]" in pt for pt in result.pontos_atencao)
        assert "Preparar contestacao" in result.proximos_passos

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_handles_partial_response(self, mock_get_llm):
        """18. Handles partial LLM response (only resumo_executivo)."""
        llm_response = json.dumps({
            "resumo_executivo": "Resumo parcial do processo.",
            # other fields missing
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)

        assert result.resumo_executivo == "Resumo parcial do processo."
        # situacao_atual should remain None
        assert result.resumo_situacao_atual is None


# =========================================================================
# 19-20  AnalisadorJurisprudenciaML
# =========================================================================

class TestAnalisadorJurisprudenciaML:

    def _make_agent(self, use_llm=True):
        agent = AnalisadorJurisprudenciaML()
        agent.use_llm = use_llm
        return agent

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_fallback_when_llm_unavailable(self, mock_get_llm):
        """19. Falls back to heuristic when LLM unavailable."""
        mock_client = MagicMock()
        mock_client.available = False
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)
        assert isinstance(result, ProcessoCanonical)

    @patch("djen.agents.ml_agents.get_llm_client")
    def test_successful_jurisprudence_identification(self, mock_get_llm):
        """20. Successfully identifies jurisprudence from LLM response."""
        llm_response = json.dumps({
            "teses": [
                {
                    "tese": "Dano moral in re ipsa",
                    "referencia": "Sumula 385/STJ",
                    "tribunal": "STJ",
                    "favorabilidade": 0.8,
                    "aplicabilidade": "Inscricao indevida comprovada",
                },
            ],
            "analise_geral": "Jurisprudencia consolidada favoravel.",
            "favorabilidade_geral": 0.75,
        })
        mock_client = MagicMock()
        mock_client.available = True
        mock_client.chat.return_value = llm_response
        mock_get_llm.return_value = mock_client

        agent = self._make_agent()
        p = _make_processo()
        result = agent.execute(p)

        # Should have added jurisprudence point
        juris_points = [pt for pt in result.pontos_atencao if "JURISPRUDENCIA ML" in pt]
        assert len(juris_points) >= 1
        assert "Sumula 385/STJ" in juris_points[0]

        # Should have added risk indicator
        juris_indicators = [
            i for i in result.indicadores_risco if i.categoria == "jurisprudencia"
        ]
        assert len(juris_indicators) == 1
        assert juris_indicators[0].nivel == NivelRisco.baixo
        assert juris_indicators[0].score == 0.25  # 1 - 0.75


# =========================================================================
# 21-24  ML Agent Swap / Registry
# =========================================================================

class TestMLAgentSwap:

    def test_ml_agent_map_contains_correct_mappings(self):
        """21. ML_AGENT_MAP contains correct mappings."""
        expected = {
            "classificador_causa": "classificador_causa_ml",
            "previsor_resultado": "previsor_resultado_ml",
            "gerador_resumo": "gerador_resumo_ml",
            "analisador_jurisprudencia": "analisador_jurisprudencia_ml",
        }
        assert ML_AGENT_MAP == expected

    def test_ml_agents_registered_in_registry(self):
        """22. ML agents are registered in AgentRegistry."""
        registry = AgentRegistry.all()
        for ml_name in ML_AGENT_MAP.values():
            assert ml_name in registry, f"{ml_name} not found in AgentRegistry"

    def test_ml_agents_same_dependencies(self):
        """23. ML agents have same dependencies as heuristic counterparts."""
        heuristic_map = {
            "classificador_causa": ClassificadorCausa,
            "previsor_resultado": PrevisorResultado,
            "gerador_resumo": GeradorResumo,
            "analisador_jurisprudencia": AnalisadorJurisprudencia,
        }
        ml_classes = {
            "classificador_causa": ClassificadorCausaML,
            "previsor_resultado": PrevisorResultadoML,
            "gerador_resumo": GeradorResumoML,
            "analisador_jurisprudencia": AnalisadorJurisprudenciaML,
        }
        for key in heuristic_map:
            h_deps = sorted(heuristic_map[key].depends_on)
            ml_deps = sorted(ml_classes[key].depends_on)
            assert h_deps == ml_deps, (
                f"Deps mismatch for {key}: heuristic={h_deps}, ml={ml_deps}"
            )

    def test_ml_agents_same_priority(self):
        """24. ML agents have same priority as heuristic counterparts."""
        heuristic_map = {
            "classificador_causa": ClassificadorCausa,
            "previsor_resultado": PrevisorResultado,
            "gerador_resumo": GeradorResumo,
            "analisador_jurisprudencia": AnalisadorJurisprudencia,
        }
        ml_classes = {
            "classificador_causa": ClassificadorCausaML,
            "previsor_resultado": PrevisorResultadoML,
            "gerador_resumo": GeradorResumoML,
            "analisador_jurisprudencia": AnalisadorJurisprudenciaML,
        }
        for key in heuristic_map:
            assert heuristic_map[key].priority == ml_classes[key].priority, (
                f"Priority mismatch for {key}"
            )
