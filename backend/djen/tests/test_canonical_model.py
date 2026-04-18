"""
Tests for djen/agents/canonical_model.py
"""

import json
import pytest
from pydantic import ValidationError

from djen.agents.canonical_model import (
    StatusProcesso,
    NivelRisco,
    PoloProcessual,
    TipoParte,
    FaseProcessual,
    AgentStatus,
    Advogado,
    ParteProcessual,
    Movimentacao,
    Comunicacao,
    ValorPecuniario,
    Prazo,
    EventoTimeline,
    IndicadorRisco,
    AgentResult,
    ProcessoCanonical,
    ProcessoResponse,
    ProcessoResumoResponse,
    TimelineResponse,
    RiscoResponse,
    PipelineStatusResponse,
)


# =========================================================================
# Enum tests
# =========================================================================

class TestStatusProcesso:
    def test_values(self):
        expected = {"ativo", "suspenso", "arquivado", "baixado", "extinto", "desconhecido"}
        assert {e.value for e in StatusProcesso} == expected

    def test_is_str(self):
        assert isinstance(StatusProcesso.ativo, str)
        assert StatusProcesso.ativo == "ativo"


class TestNivelRisco:
    def test_values(self):
        expected = {"muito_baixo", "baixo", "medio", "alto", "critico"}
        assert {e.value for e in NivelRisco} == expected


class TestPoloProcessual:
    def test_values(self):
        expected = {"ativo", "passivo", "terceiro", "interessado", "ministerio_publico", "desconhecido"}
        assert {e.value for e in PoloProcessual} == expected


class TestTipoParte:
    def test_values(self):
        expected = {"pessoa_fisica", "pessoa_juridica", "ente_publico", "desconhecido"}
        assert {e.value for e in TipoParte} == expected


class TestFaseProcessual:
    def test_values(self):
        expected = {"conhecimento", "recursal", "execucao", "cumprimento", "liquidacao", "cautelar", "desconhecida"}
        assert {e.value for e in FaseProcessual} == expected


class TestAgentStatus:
    def test_values(self):
        expected = {"pending", "running", "completed", "failed", "skipped"}
        assert {e.value for e in AgentStatus} == expected


# =========================================================================
# Sub-model tests
# =========================================================================

class TestAdvogado:
    def test_minimal(self):
        adv = Advogado(nome="João Silva")
        assert adv.nome == "João Silva"
        assert adv.oab is None
        assert adv.uf_oab is None
        assert adv.polo is None

    def test_full(self):
        adv = Advogado(nome="Maria", oab="12345", uf_oab="SP", polo=PoloProcessual.ativo)
        assert adv.oab == "12345"
        assert adv.polo == PoloProcessual.ativo

    def test_serialization(self):
        adv = Advogado(nome="Test", oab="999", uf_oab="RJ", polo=PoloProcessual.passivo)
        d = adv.model_dump()
        assert d["nome"] == "Test"
        assert d["polo"] == "passivo"


class TestParteProcessual:
    def test_defaults(self):
        p = ParteProcessual(nome="Empresa X")
        assert p.tipo == TipoParte.desconhecido
        assert p.polo == PoloProcessual.desconhecido
        assert p.cpf_cnpj is None
        assert p.advogados == []

    def test_with_advogados(self):
        adv = Advogado(nome="Adv1")
        p = ParteProcessual(nome="Pessoa", tipo=TipoParte.pessoa_fisica, advogados=[adv])
        assert len(p.advogados) == 1


class TestMovimentacao:
    def test_creation(self):
        m = Movimentacao(nome="Despacho", data="2024-01-01")
        assert m.codigo is None
        assert m.complemento is None
        assert m.tipo is None

    def test_full(self):
        m = Movimentacao(codigo=123, nome="Sentença", data="2024-06-15", complemento="Procedente", tipo="sentenca")
        assert m.codigo == 123
        assert m.tipo == "sentenca"


class TestComunicacao:
    def test_minimal(self):
        c = Comunicacao(tipo="Intimacao", data_disponibilizacao="2024-01-01")
        assert c.id is None
        assert c.destinatarios == []
        assert c.advogados_destinatarios == []

    def test_with_nested_advogados(self):
        advs = [Advogado(nome="Adv1"), Advogado(nome="Adv2")]
        c = Comunicacao(
            tipo="Citacao",
            data_disponibilizacao="2024-02-01",
            texto="Texto",
            meio="eletronica",
            orgao="TJSP",
            destinatarios=["Dest1"],
            advogados_destinatarios=advs,
        )
        assert len(c.advogados_destinatarios) == 2
        assert c.advogados_destinatarios[0].nome == "Adv1"


class TestValorPecuniario:
    def test_creation(self):
        v = ValorPecuniario(tipo="causa", valor=10000.50)
        assert v.moeda == "BRL"
        assert v.data_referencia is None

    def test_full(self):
        v = ValorPecuniario(tipo="condenacao", valor=5000.0, moeda="USD", data_referencia="2024-01-01", descricao="desc")
        assert v.moeda == "USD"


class TestPrazo:
    def test_defaults(self):
        p = Prazo(tipo="recurso", data_fim="2024-12-31")
        assert p.util is True
        assert p.urgente is False
        assert p.data_inicio is None

    def test_urgente(self):
        p = Prazo(tipo="manifestacao", data_fim="2024-06-01", urgente=True, dias_restantes=3)
        assert p.urgente is True
        assert p.dias_restantes == 3


class TestEventoTimeline:
    def test_default_relevancia(self):
        e = EventoTimeline(data="2024-01-01", titulo="Distribuição", tipo="distribuicao")
        assert e.relevancia == 5

    def test_relevancia_bounds_valid(self):
        e1 = EventoTimeline(data="2024-01-01", titulo="T", tipo="t", relevancia=1)
        assert e1.relevancia == 1
        e10 = EventoTimeline(data="2024-01-01", titulo="T", tipo="t", relevancia=10)
        assert e10.relevancia == 10

    def test_relevancia_too_low(self):
        with pytest.raises(ValidationError):
            EventoTimeline(data="2024-01-01", titulo="T", tipo="t", relevancia=0)

    def test_relevancia_too_high(self):
        with pytest.raises(ValidationError):
            EventoTimeline(data="2024-01-01", titulo="T", tipo="t", relevancia=11)


class TestIndicadorRisco:
    def test_creation(self):
        i = IndicadorRisco(categoria="prazo", nivel=NivelRisco.alto, score=0.8, descricao="Prazo curto")
        assert i.recomendacao is None

    def test_score_bounds_valid(self):
        IndicadorRisco(categoria="a", nivel=NivelRisco.baixo, score=0.0, descricao="d")
        IndicadorRisco(categoria="a", nivel=NivelRisco.baixo, score=1.0, descricao="d")

    def test_score_too_low(self):
        with pytest.raises(ValidationError):
            IndicadorRisco(categoria="a", nivel=NivelRisco.baixo, score=-0.1, descricao="d")

    def test_score_too_high(self):
        with pytest.raises(ValidationError):
            IndicadorRisco(categoria="a", nivel=NivelRisco.baixo, score=1.1, descricao="d")


class TestAgentResult:
    def test_creation(self):
        ar = AgentResult(agent_name="scraper", status=AgentStatus.completed)
        assert ar.data == {}
        assert ar.error is None

    def test_full(self):
        ar = AgentResult(
            agent_name="enricher",
            status=AgentStatus.failed,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:01:00",
            duration_ms=60000,
            error="timeout",
            data={"key": "value"},
        )
        assert ar.error == "timeout"
        assert ar.data["key"] == "value"


# =========================================================================
# ProcessoCanonical tests
# =========================================================================

class TestProcessoCanonical:
    def test_minimal(self):
        p = ProcessoCanonical(numero_processo="0000001-00.2024.8.26.0001")
        assert p.numero_processo == "0000001-00.2024.8.26.0001"
        assert p.status == StatusProcesso.desconhecido
        assert p.fase == FaseProcessual.desconhecida
        assert p.risco_geral == NivelRisco.medio
        assert p.risco_score == 0.5
        assert p.partes == []
        assert p.movimentacoes == []
        assert p.nivel_sigilo == 0
        assert p.total_partes == 0

    def test_all_fields(self):
        adv = Advogado(nome="Adv", oab="111", uf_oab="SP")
        parte = ParteProcessual(nome="Parte1", advogados=[adv])
        mov = Movimentacao(nome="Mov1", data="2024-01-01")
        com = Comunicacao(tipo="Intimacao", data_disponibilizacao="2024-01-01")
        val = ValorPecuniario(tipo="causa", valor=1000.0)
        prazo = Prazo(tipo="recurso", data_fim="2024-12-31")
        evento = EventoTimeline(data="2024-01-01", titulo="Evt", tipo="dist")
        indicador = IndicadorRisco(categoria="prazo", nivel=NivelRisco.alto, score=0.9, descricao="Alto risco")
        agent = AgentResult(agent_name="ag1", status=AgentStatus.completed)

        p = ProcessoCanonical(
            numero_processo="123",
            numero_formatado="0000123",
            tribunal="TJSP",
            grau="G1",
            justica="estadual",
            classe_processual="Ação Civil",
            classe_codigo=100,
            assuntos=["Direito Civil"],
            assuntos_codigos=[1001],
            area="civel",
            fase=FaseProcessual.conhecimento,
            status=StatusProcesso.ativo,
            orgao_julgador="1ª Vara",
            orgao_codigo=1,
            comarca="São Paulo",
            uf="SP",
            municipio_ibge=3550308,
            data_ajuizamento="2024-01-01",
            data_ultima_movimentacao="2024-06-01",
            data_distribuicao="2024-01-01",
            data_sentenca=None,
            data_transito_julgado=None,
            duracao_dias=180,
            partes=[parte],
            advogados=[adv],
            total_partes=1,
            movimentacoes=[mov],
            total_movimentacoes=1,
            ultima_movimentacao=mov,
            comunicacoes=[com],
            total_comunicacoes=1,
            valores=[val],
            valor_causa=1000.0,
            prazos=[prazo],
            prazo_mais_urgente=prazo,
            timeline=[evento],
            risco_geral=NivelRisco.alto,
            risco_score=0.9,
            indicadores_risco=[indicador],
            resumo_executivo="Resumo",
            resumo_situacao_atual="Atual",
            pontos_atencao=["Ponto 1"],
            proximos_passos=["Passo 1"],
            formato_origem="Eletronico",
            sistema_origem="PJe",
            nivel_sigilo=1,
            fontes_consultadas=["DataJud"],
            agents_executed=[agent],
            enriched_at="2024-06-01T12:00:00",
            processing_time_ms=5000,
            raw_datajud={"key": "val"},
            raw_djen=[{"k": "v"}],
        )
        assert p.tribunal == "TJSP"
        assert p.risco_score == 0.9
        assert len(p.partes) == 1
        assert p.raw_datajud == {"key": "val"}

    def test_risco_score_invalid_high(self):
        with pytest.raises(ValidationError):
            ProcessoCanonical(numero_processo="123", risco_score=1.5)

    def test_risco_score_invalid_low(self):
        with pytest.raises(ValidationError):
            ProcessoCanonical(numero_processo="123", risco_score=-0.1)

    def test_missing_numero_processo(self):
        with pytest.raises(ValidationError):
            ProcessoCanonical()


# =========================================================================
# Response model tests
# =========================================================================

class TestProcessoResponse:
    def test_creation(self):
        proc = ProcessoCanonical(numero_processo="123")
        resp = ProcessoResponse(processo=proc)
        assert resp.status == "success"
        assert resp.visao == "completa"
        assert resp.tempo_processamento_ms == 0

    def test_custom_values(self):
        proc = ProcessoCanonical(numero_processo="456")
        resp = ProcessoResponse(processo=proc, visao="timeline", tempo_processamento_ms=1500)
        assert resp.visao == "timeline"


class TestProcessoResumoResponse:
    def test_creation(self):
        r = ProcessoResumoResponse(
            numero_processo="123",
            tribunal="TJSP",
            classe_processual="Ação",
            status="ativo",
            fase="conhecimento",
            risco_geral="medio",
            risco_score=0.5,
            resumo_executivo="Resumo",
            pontos_atencao=["P1"],
            proximos_passos=["N1"],
            prazo_mais_urgente=None,
            valor_causa=1000.0,
            total_partes=2,
            total_movimentacoes=5,
            total_comunicacoes=3,
            duracao_dias=100,
        )
        assert r.numero_processo == "123"
        assert r.risco_score == 0.5


class TestTimelineResponse:
    def test_creation(self):
        evt = EventoTimeline(data="2024-01-01", titulo="E1", tipo="dist")
        r = TimelineResponse(numero_processo="123", total_eventos=1, timeline=[evt])
        assert r.total_eventos == 1
        assert len(r.timeline) == 1


class TestRiscoResponse:
    def test_creation(self):
        ind = IndicadorRisco(categoria="prazo", nivel=NivelRisco.alto, score=0.8, descricao="desc")
        r = RiscoResponse(
            numero_processo="123",
            risco_geral=NivelRisco.alto,
            risco_score=0.8,
            indicadores=[ind],
            recomendacoes=["Rec1"],
        )
        assert r.risco_geral == NivelRisco.alto
        assert len(r.indicadores) == 1


class TestPipelineStatusResponse:
    def test_creation(self):
        ag = AgentResult(agent_name="ag1", status=AgentStatus.running)
        r = PipelineStatusResponse(
            numero_processo="123",
            status="running",
            agents=[ag],
            progress_percent=50.0,
            elapsed_ms=3000,
        )
        assert r.progress_percent == 50.0
        assert r.elapsed_ms == 3000


# =========================================================================
# Serialization roundtrip
# =========================================================================

class TestSerializationRoundtrip:
    def test_processo_canonical_roundtrip(self):
        original = ProcessoCanonical(
            numero_processo="999",
            tribunal="TJRJ",
            status=StatusProcesso.ativo,
            fase=FaseProcessual.recursal,
            risco_geral=NivelRisco.critico,
            risco_score=0.95,
            partes=[ParteProcessual(nome="P1", tipo=TipoParte.pessoa_fisica)],
            timeline=[EventoTimeline(data="2024-01-01", titulo="T", tipo="t", relevancia=7)],
        )
        json_str = original.model_dump_json()
        restored = ProcessoCanonical.model_validate_json(json_str)
        assert restored.numero_processo == original.numero_processo
        assert restored.tribunal == original.tribunal
        assert restored.status == original.status
        assert restored.fase == original.fase
        assert restored.risco_score == original.risco_score
        assert len(restored.partes) == 1
        assert restored.partes[0].nome == "P1"
        assert restored.timeline[0].relevancia == 7

    def test_advogado_roundtrip(self):
        adv = Advogado(nome="Test", oab="123", polo=PoloProcessual.ativo)
        restored = Advogado.model_validate_json(adv.model_dump_json())
        assert restored == adv

    def test_indicador_risco_roundtrip(self):
        ind = IndicadorRisco(categoria="fin", nivel=NivelRisco.baixo, score=0.2, descricao="ok", recomendacao="none")
        restored = IndicadorRisco.model_validate_json(ind.model_dump_json())
        assert restored == ind

    def test_response_roundtrip(self):
        proc = ProcessoCanonical(numero_processo="111")
        resp = ProcessoResponse(processo=proc, visao="risco", tempo_processamento_ms=200)
        restored = ProcessoResponse.model_validate_json(resp.model_dump_json())
        assert restored.processo.numero_processo == "111"
        assert restored.visao == "risco"


# =========================================================================
# Default values
# =========================================================================

class TestDefaultValues:
    def test_processo_defaults(self):
        p = ProcessoCanonical(numero_processo="X")
        assert p.fase == FaseProcessual.desconhecida
        assert p.status == StatusProcesso.desconhecido
        assert p.risco_geral == NivelRisco.medio
        assert p.risco_score == 0.5
        assert p.nivel_sigilo == 0
        assert p.total_partes == 0
        assert p.total_movimentacoes == 0
        assert p.total_comunicacoes == 0
        assert p.assuntos == []
        assert p.fontes_consultadas == []
        assert p.agents_executed == []

    def test_valor_pecuniario_default_moeda(self):
        v = ValorPecuniario(tipo="causa", valor=100)
        assert v.moeda == "BRL"

    def test_prazo_defaults(self):
        p = Prazo(tipo="recurso", data_fim="2024-12-31")
        assert p.util is True
        assert p.urgente is False

    def test_evento_timeline_default_relevancia(self):
        e = EventoTimeline(data="2024-01-01", titulo="T", tipo="t")
        assert e.relevancia == 5

    def test_parte_processual_defaults(self):
        p = ParteProcessual(nome="N")
        assert p.tipo == TipoParte.desconhecido
        assert p.polo == PoloProcessual.desconhecido

    def test_agent_result_defaults(self):
        ar = AgentResult(agent_name="a", status=AgentStatus.pending)
        assert ar.data == {}
        assert ar.error is None
        assert ar.duration_ms is None

    def test_processo_response_defaults(self):
        resp = ProcessoResponse(processo=ProcessoCanonical(numero_processo="X"))
        assert resp.status == "success"
        assert resp.visao == "completa"
        assert resp.tempo_processamento_ms == 0
