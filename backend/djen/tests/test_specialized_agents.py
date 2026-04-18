"""
Testes para os 14 agentes especializados em djen/agents/specialized.py.

Todos os testes usam dados pre-populados (sem chamadas de rede).
"""

import pytest
from datetime import datetime, timedelta

from djen.agents.canonical_model import (
    ProcessoCanonical, Advogado, ParteProcessual, Movimentacao,
    Comunicacao, ValorPecuniario, Prazo, EventoTimeline,
    IndicadorRisco, StatusProcesso, NivelRisco, PoloProcessual,
    TipoParte, FaseProcessual,
)
from djen.agents.specialized import (
    ValidadorProcessual,
    ColetorDatajud,
    ColetorDjen,
    ExtratorEntidades,
    AnalisadorMovimentacoes,
    ClassificadorCausa,
    ExtratorValores,
    AnalisadorCronologia,
    CalculadorPrazos,
    AnalisadorRisco,
    GeradorResumo,
    AnalisadorJurisprudencia,
    ValidadorConformidade,
    PrevisorResultado,
)


# =========================================================================
# Helpers
# =========================================================================

def _make_processo(numero: str = "00012345620238260001", **kwargs) -> ProcessoCanonical:
    return ProcessoCanonical(numero_processo=numero, **kwargs)


# =========================================================================
# 1. ValidadorProcessual
# =========================================================================

class TestValidadorProcessual:
    def setup_method(self):
        self.agent = ValidadorProcessual()

    def test_normalize_20_digit_number(self):
        p = _make_processo("00012345620238260001")
        result = self.agent.execute(p)
        assert result.numero_formatado == "0001234-56.2023.8.26.0001"

    def test_normalize_formatted_number(self):
        p = _make_processo("0001234-56.2023.8.26.0001")
        result = self.agent.execute(p)
        assert result.numero_formatado == "0001234-56.2023.8.26.0001"

    def test_justica_estadual(self):
        # J=8 => estadual
        p = _make_processo("00012345620238260001")
        result = self.agent.execute(p)
        assert result.justica == "estadual"

    def test_justica_federal(self):
        # J=5 => federal
        p = _make_processo("00012345620235010001")
        result = self.agent.execute(p)
        assert result.justica == "federal"

    def test_justica_trabalho(self):
        # J=9 => trabalho
        p = _make_processo("00012345620239010001")
        result = self.agent.execute(p)
        assert result.justica == "trabalho"

    def test_strips_whitespace(self):
        p = _make_processo("  00012345620238260001  ")
        result = self.agent.execute(p)
        assert result.numero_formatado is not None

    def test_fontes_consultadas_initialized(self):
        p = _make_processo("00012345620238260001")
        result = self.agent.execute(p)
        assert result.fontes_consultadas == []

    def test_non_standard_number_uses_original(self):
        p = _make_processo("12345")
        result = self.agent.execute(p)
        assert result.numero_formatado == "12345"


# =========================================================================
# 2. ColetorDatajud - _detect_tribunal only
# =========================================================================

class TestColetorDatajud:
    def setup_method(self):
        self.agent = ColetorDatajud()

    def test_detect_tribunal_tjsp(self):
        # J=8, TR=26 => tjsp
        result = self.agent._detect_tribunal("00012345620238260001")
        assert result == "tjsp"

    def test_detect_tribunal_tjrj(self):
        # J=8, TR=19 => tjrj
        result = self.agent._detect_tribunal("00012345620238190001")
        assert result == "tjrj"

    def test_detect_tribunal_federal(self):
        # J=5, TR=01 => trf01
        result = self.agent._detect_tribunal("00012345620235010001")
        assert result == "trf01"

    def test_detect_tribunal_trt(self):
        # J=4, TR=02 => trf02
        result = self.agent._detect_tribunal("00012345620234020001")
        assert result == "trf02"

    def test_detect_tribunal_short_number(self):
        result = self.agent._detect_tribunal("12345")
        assert result is None

    def test_detect_tribunal_tjmg(self):
        # J=8, TR=13 => tjmg
        result = self.agent._detect_tribunal("00012345620238130001")
        assert result == "tjmg"


# =========================================================================
# 3. ColetorDjen - can_execute only (no network)
# =========================================================================

class TestColetorDjen:
    def setup_method(self):
        self.agent = ColetorDjen()

    def test_agent_name(self):
        assert self.agent.name == "coletor_djen"

    def test_depends_on_validador(self):
        assert "validador" in self.agent.depends_on

    def test_priority(self):
        assert self.agent.priority == 1


# =========================================================================
# 4. ExtratorEntidades
# =========================================================================

class TestExtratorEntidades:
    def setup_method(self):
        self.agent = ExtratorEntidades()

    def test_extract_destinatarios_as_partes(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                destinatarios=["JOAO DA SILVA", "MARIA DE SOUZA"],
            )
        ]
        result = self.agent.execute(p)
        nomes = [parte.nome for parte in result.partes]
        assert "JOAO DA SILVA" in nomes
        assert "MARIA DE SOUZA" in nomes

    def test_extract_advogados_from_comunicacao(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                advogados_destinatarios=[
                    Advogado(nome="Dr. Teste", oab="12345", uf_oab="SP"),
                ],
            )
        ]
        result = self.agent.execute(p)
        assert len(result.advogados) == 1
        assert result.advogados[0].oab == "12345"

    def test_oab_pattern_matching(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="Advogado OAB: SP 98765 presente na audiencia",
            )
        ]
        result = self.agent.execute(p)
        oabs = [(a.oab, a.uf_oab) for a in result.advogados]
        assert ("98765", "SP") in oabs

    def test_oab_pattern_slash_format(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="Advogado inscrito sob o numero 54321/RJ",
            )
        ]
        result = self.agent.execute(p)
        oabs = [(a.oab, a.uf_oab) for a in result.advogados]
        assert ("54321", "RJ") in oabs

    def test_polo_detection_ativo(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                destinatarios=["JOAO DA SILVA"],
                texto="AUTOR JOAO DA SILVA ajuizou a presente acao",
            )
        ]
        result = self.agent.execute(p)
        joao = [parte for parte in result.partes if parte.nome == "JOAO DA SILVA"][0]
        assert joao.polo == PoloProcessual.ativo

    def test_polo_detection_passivo(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                destinatarios=["EMPRESA LTDA"],
                texto="em face do REU EMPRESA LTDA nestes autos",
            )
        ]
        result = self.agent.execute(p)
        empresa = [parte for parte in result.partes if parte.nome == "EMPRESA LTDA"][0]
        assert empresa.polo == PoloProcessual.passivo

    def test_tipo_parte_ente_publico(self):
        assert self.agent._detect_tipo_parte("ESTADO DE SAO PAULO") == TipoParte.ente_publico
        assert self.agent._detect_tipo_parte("INSS") == TipoParte.ente_publico
        assert self.agent._detect_tipo_parte("FAZENDA PUBLICA") == TipoParte.ente_publico

    def test_tipo_parte_pessoa_juridica(self):
        assert self.agent._detect_tipo_parte("EMPRESA LTDA") == TipoParte.pessoa_juridica
        assert self.agent._detect_tipo_parte("BANCO DO BRASIL S/A") == TipoParte.pessoa_juridica

    def test_tipo_parte_pessoa_fisica(self):
        assert self.agent._detect_tipo_parte("JOAO DA SILVA") == TipoParte.pessoa_fisica

    def test_total_partes_count(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                destinatarios=["A", "B", "C"],
            )
        ]
        result = self.agent.execute(p)
        assert result.total_partes == 3


# =========================================================================
# 5. AnalisadorMovimentacoes
# =========================================================================

class TestAnalisadorMovimentacoes:
    def setup_method(self):
        self.agent = AnalisadorMovimentacoes()

    def test_classify_by_codigo_sentenca(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=22, nome="Sentença", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "sentenca"

    def test_classify_by_codigo_despacho(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=11, nome="Despacho", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "despacho"

    def test_classify_by_codigo_distribuicao(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=26, nome="Distribuicao", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "distribuicao"

    def test_classify_by_nome_sentenca(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=9999, nome="Proferida sentença", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "sentenca"

    def test_classify_by_nome_despacho(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=9999, nome="Despacho proferido", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "despacho"

    def test_classify_by_nome_decisao(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=9999, nome="Decisão interlocutória", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "decisao"

    def test_classify_by_nome_recurso(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=9999, nome="Recurso de apelação", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "recurso"

    def test_classify_by_nome_outro(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=9999, nome="Evento genérico XYZ", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.movimentacoes[0].tipo == "outro"

    def test_status_arquivado(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=246, nome="Arquivamento", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.status == StatusProcesso.arquivado

    def test_status_extinto(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=848, nome="Trânsito em julgado", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.status == StatusProcesso.extinto

    def test_status_ativo(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(codigo=11, nome="Despacho", data="2024-01-01")]
        result = self.agent.execute(p)
        assert result.status == StatusProcesso.ativo

    def test_data_sentenca_detected(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(codigo=11, nome="Despacho", data="2024-02-01"),
            Movimentacao(codigo=22, nome="Sentenca", data="2024-01-15"),
        ]
        result = self.agent.execute(p)
        assert result.data_sentenca == "2024-01-15"

    def test_data_transito_julgado_detected(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(codigo=848, nome="Transito em julgado", data="2024-03-01"),
        ]
        result = self.agent.execute(p)
        assert result.data_transito_julgado == "2024-03-01"


# =========================================================================
# 6. ClassificadorCausa
# =========================================================================

class TestClassificadorCausa:
    def setup_method(self):
        self.agent = ClassificadorCausa()

    def test_area_criminal(self):
        p = _make_processo()
        p.classe_processual = "Ação Penal"
        result = self.agent.execute(p)
        assert result.area == "criminal"

    def test_area_trabalhista(self):
        p = _make_processo()
        p.assuntos = ["Reclamação Trabalhista"]
        result = self.agent.execute(p)
        assert result.area == "trabalhista"

    def test_area_tributaria(self):
        p = _make_processo()
        p.assuntos = ["Execução Fiscal"]
        result = self.agent.execute(p)
        assert result.area == "tributaria"

    def test_area_familia(self):
        p = _make_processo()
        p.assuntos = ["Alimentos"]
        result = self.agent.execute(p)
        assert result.area == "familia"

    def test_area_consumidor(self):
        p = _make_processo()
        p.classe_processual = "Direito do Consumidor"
        result = self.agent.execute(p)
        assert result.area == "consumidor"

    def test_area_civel_default(self):
        p = _make_processo()
        p.classe_processual = "Procedimento Comum"
        result = self.agent.execute(p)
        assert result.area == "civel"

    def test_fase_recursal(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(nome="Recurso", data="2024-01-01", tipo="recurso"),
        ]
        result = self.agent.execute(p)
        assert result.fase == FaseProcessual.recursal

    def test_fase_execucao(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(nome="TJ", data="2024-01-01", tipo="transito_julgado"),
        ]
        result = self.agent.execute(p)
        assert result.fase == FaseProcessual.execucao

    def test_fase_conhecimento(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(nome="Despacho", data="2024-01-01", tipo="despacho"),
        ]
        result = self.agent.execute(p)
        assert result.fase == FaseProcessual.conhecimento

    def test_fase_desconhecida_no_movimentacoes(self):
        p = _make_processo()
        result = self.agent.execute(p)
        assert result.fase == FaseProcessual.desconhecida


# =========================================================================
# 7. ExtratorValores
# =========================================================================

class TestExtratorValores:
    def setup_method(self):
        self.agent = ExtratorValores()

    def test_extract_simple_value(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="O valor da causa é de R$ 10.000,00 conforme petição inicial.",
            )
        ]
        result = self.agent.execute(p)
        assert len(result.valores) >= 1
        assert any(v.valor == 10000.0 for v in result.valores)

    def test_tipo_causa_detected(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="Valor da causa R$ 50.000,00",
            )
        ]
        result = self.agent.execute(p)
        causa_vals = [v for v in result.valores if v.tipo == "causa"]
        assert len(causa_vals) >= 1
        assert result.valor_causa == 50000.0

    def test_tipo_condenacao_detected(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="Fixo a condenação em R$ 20.000,00 a título de danos morais.",
            )
        ]
        result = self.agent.execute(p)
        cond_vals = [v for v in result.valores if v.tipo == "condenacao"]
        assert len(cond_vals) >= 1

    def test_tipo_honorarios_detected(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="Honorários advocatícios fixados em R$ 5.000,00",
            )
        ]
        result = self.agent.execute(p)
        hon_vals = [v for v in result.valores if v.tipo == "honorarios"]
        assert len(hon_vals) >= 1

    def test_ignores_tiny_values(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto="Valor R$ 0,01 irrelevante",
            )
        ]
        result = self.agent.execute(p)
        assert len(result.valores) == 0

    def test_no_values_in_empty_text(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-01",
                texto=None,
            )
        ]
        result = self.agent.execute(p)
        assert len(result.valores) == 0


# =========================================================================
# 8. AnalisadorCronologia
# =========================================================================

class TestAnalisadorCronologia:
    def setup_method(self):
        self.agent = AnalisadorCronologia()

    def test_timeline_from_movimentacoes(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(nome="Sentenca", data="2024-02-01", tipo="sentenca"),
            Movimentacao(nome="Distribuicao", data="2024-01-01", tipo="distribuicao"),
        ]
        result = self.agent.execute(p)
        # Both have relevancia >= 4 so both should appear
        tipos = [e.tipo for e in result.timeline]
        assert "sentenca" in tipos
        assert "distribuicao" in tipos

    def test_timeline_filters_low_relevance(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(nome="Juntada", data="2024-01-01", tipo="juntada"),
        ]
        result = self.agent.execute(p)
        # juntada has relevancia 2, so it should NOT appear
        mov_events = [e for e in result.timeline if e.tipo == "juntada"]
        assert len(mov_events) == 0

    def test_timeline_includes_comunicacoes(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao="2024-01-15",
                orgao="1a Vara Civel",
            )
        ]
        result = self.agent.execute(p)
        com_events = [e for e in result.timeline if e.tipo == "comunicacao"]
        assert len(com_events) == 1

    def test_timeline_ordering_descending(self):
        p = _make_processo()
        p.movimentacoes = [
            Movimentacao(nome="Distribuicao", data="2024-01-01", tipo="distribuicao"),
            Movimentacao(nome="Sentenca", data="2024-06-01", tipo="sentenca"),
        ]
        result = self.agent.execute(p)
        dates = [e.data for e in result.timeline]
        assert dates == sorted(dates, reverse=True)

    def test_duracao_calculation(self):
        p = _make_processo()
        p.data_ajuizamento = "2022-01-01"
        result = self.agent.execute(p)
        assert result.duracao_dias is not None
        assert result.duracao_dias > 0


# =========================================================================
# 9. CalculadorPrazos
# =========================================================================

class TestCalculadorPrazos:
    def setup_method(self):
        self.agent = CalculadorPrazos()

    def test_detect_prazo_from_text(self):
        future = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao=future,
                texto="Fica intimado no prazo de 15 dias para se manifestar nos autos.",
            )
        ]
        result = self.agent.execute(p)
        assert len(result.prazos) >= 1
        assert result.prazos[0].tipo == "manifestacao"

    def test_detect_prazo_cumprimento(self):
        future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao=future,
                texto="Concedo 30 dias para cumprir a obrigação.",
            )
        ]
        result = self.agent.execute(p)
        assert len(result.prazos) >= 1
        assert result.prazos[0].tipo == "cumprimento"

    def test_urgency_calculation(self):
        # Publication date is today minus 10 days, prazo of 12 days => 2 days left => urgent
        past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao=past,
                texto="Prazo de 12 dias para se manifestar.",
            )
        ]
        result = self.agent.execute(p)
        assert len(result.prazos) >= 1
        assert result.prazos[0].urgente is True

    def test_ordering_by_urgency(self):
        today = datetime.now().strftime("%Y-%m-%d")
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao=today,
                texto="Prazo de 30 dias para se manifestar.",
            ),
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao=today,
                texto="Prazo de 5 dias para cumprir a sentença.",
            ),
        ]
        result = self.agent.execute(p)
        if len(result.prazos) >= 2:
            assert result.prazos[0].dias_restantes <= result.prazos[1].dias_restantes

    def test_prazo_mais_urgente_set(self):
        today = datetime.now().strftime("%Y-%m-%d")
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(
                tipo="Intimacao",
                data_disponibilizacao=today,
                texto="No prazo de 10 dias uteis para manifestar.",
            )
        ]
        result = self.agent.execute(p)
        assert result.prazo_mais_urgente is not None


# =========================================================================
# 10. AnalisadorRisco
# =========================================================================

class TestAnalisadorRisco:
    def setup_method(self):
        self.agent = AnalisadorRisco()

    def test_risco_prazo_vencido_critico(self):
        p = _make_processo()
        p.prazos = [Prazo(tipo="manifestacao", data_fim="2024-01-01", dias_restantes=-5, urgente=True)]
        p.prazo_mais_urgente = p.prazos[0]
        result = self.agent.execute(p)
        categorias = [i.categoria for i in result.indicadores_risco]
        assert "prazo" in categorias
        prazo_ind = [i for i in result.indicadores_risco if i.categoria == "prazo"][0]
        assert prazo_ind.nivel == NivelRisco.critico

    def test_risco_prazo_proximo_alto(self):
        p = _make_processo()
        p.prazos = [Prazo(tipo="manifestacao", data_fim="2024-01-01", dias_restantes=2, urgente=True)]
        p.prazo_mais_urgente = p.prazos[0]
        result = self.agent.execute(p)
        prazo_ind = [i for i in result.indicadores_risco if i.categoria == "prazo"][0]
        assert prazo_ind.nivel == NivelRisco.alto

    def test_risco_procedimental_longo(self):
        p = _make_processo()
        p.duracao_dias = 2000  # > 5 years
        result = self.agent.execute(p)
        proc_ind = [i for i in result.indicadores_risco if i.categoria == "procedimental"]
        assert len(proc_ind) >= 1
        assert proc_ind[0].nivel == NivelRisco.alto

    def test_risco_merito_recursal(self):
        p = _make_processo()
        p.fase = FaseProcessual.recursal
        result = self.agent.execute(p)
        merito_ind = [i for i in result.indicadores_risco if i.categoria == "merito"]
        assert len(merito_ind) >= 1
        assert merito_ind[0].nivel == NivelRisco.medio

    def test_risco_financeiro_alto(self):
        p = _make_processo()
        p.valor_causa = 500000.0
        result = self.agent.execute(p)
        fin_ind = [i for i in result.indicadores_risco if i.categoria == "financeiro"]
        assert len(fin_ind) >= 1
        assert fin_ind[0].nivel == NivelRisco.alto

    def test_score_calculation(self):
        p = _make_processo()
        result = self.agent.execute(p)
        assert 0.0 <= result.risco_score <= 1.0

    def test_nivel_classification_critico(self):
        p = _make_processo()
        p.prazos = [Prazo(tipo="manifestacao", data_fim="2024-01-01", dias_restantes=-10, urgente=True)]
        p.prazo_mais_urgente = p.prazos[0]
        p.duracao_dias = 2000
        p.valor_causa = 500000.0
        p.fase = FaseProcessual.recursal
        result = self.agent.execute(p)
        assert result.risco_geral in (NivelRisco.alto, NivelRisco.critico)

    def test_nivel_classification_baixo(self):
        p = _make_processo()
        # No prazos, no duracao, no valor alto => low risk
        result = self.agent.execute(p)
        assert result.risco_geral in (NivelRisco.baixo, NivelRisco.medio, NivelRisco.muito_baixo)


# =========================================================================
# 11. GeradorResumo
# =========================================================================

class TestGeradorResumo:
    def setup_method(self):
        self.agent = GeradorResumo()

    def _populated_processo(self):
        p = _make_processo()
        p.numero_formatado = "0001234-56.2023.8.26.0001"
        p.tribunal = "TJSP"
        p.classe_processual = "Procedimento Comum"
        p.orgao_julgador = "1a Vara Civel"
        p.area = "civel"
        p.fase = FaseProcessual.conhecimento
        p.status = StatusProcesso.ativo
        p.duracao_dias = 400
        p.valor_causa = 50000.0
        p.partes = [
            ParteProcessual(nome="JOAO", polo=PoloProcessual.ativo),
            ParteProcessual(nome="EMPRESA LTDA", polo=PoloProcessual.passivo),
        ]
        p.ultima_movimentacao = Movimentacao(nome="Despacho", data="2024-06-01")
        p.total_comunicacoes = 3
        p.indicadores_risco = [
            IndicadorRisco(
                categoria="prazo", nivel=NivelRisco.alto, score=0.8,
                descricao="Prazo vence em 2 dias",
            )
        ]
        p.prazo_mais_urgente = Prazo(
            tipo="manifestacao", data_fim="2024-07-01",
            dias_restantes=3, urgente=True,
            descricao="Prazo de 15 dias (manifestacao)",
        )
        p.prazos = [p.prazo_mais_urgente]
        return p

    def test_resumo_executivo_generated(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert result.resumo_executivo is not None
        assert "0001234-56.2023.8.26.0001" in result.resumo_executivo

    def test_resumo_includes_tribunal(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert "TJSP" in result.resumo_executivo

    def test_resumo_includes_area(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert "Civel" in result.resumo_executivo

    def test_pontos_atencao_from_riscos(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert len(result.pontos_atencao) >= 1

    def test_proximos_passos_ativo_conhecimento(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert any("instrucao" in s.lower() or "prazo" in s.lower() for s in result.proximos_passos)

    def test_proximos_passos_includes_prazo(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert any("prazo" in s.lower() for s in result.proximos_passos)

    def test_proximos_passos_includes_djen_check(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert any("intimacoes" in s.lower() or "djen" in s.lower() for s in result.proximos_passos)

    def test_resumo_situacao_atual(self):
        p = self._populated_processo()
        result = self.agent.execute(p)
        assert result.resumo_situacao_atual is not None
        assert "Despacho" in result.resumo_situacao_atual


# =========================================================================
# 12. AnalisadorJurisprudencia
# =========================================================================

class TestAnalisadorJurisprudencia:
    def setup_method(self):
        self.agent = AnalisadorJurisprudencia()

    def test_teses_consumidor(self):
        p = _make_processo()
        p.area = "consumidor"
        result = self.agent.execute(p)
        juris = [a for a in result.pontos_atencao if "JURISPRUDENCIA" in a]
        assert len(juris) >= 1
        assert any("CDC" in j or "consumo" in j or "inadimplentes" in j for j in juris)

    def test_teses_trabalhista(self):
        p = _make_processo()
        p.area = "trabalhista"
        result = self.agent.execute(p)
        juris = [a for a in result.pontos_atencao if "JURISPRUDENCIA" in a]
        assert len(juris) >= 1

    def test_teses_criminal(self):
        p = _make_processo()
        p.area = "criminal"
        result = self.agent.execute(p)
        juris = [a for a in result.pontos_atencao if "JURISPRUDENCIA" in a]
        assert len(juris) >= 1

    def test_teses_default_civel(self):
        p = _make_processo()
        p.area = None  # defaults to civel
        result = self.agent.execute(p)
        juris = [a for a in result.pontos_atencao if "JURISPRUDENCIA" in a]
        assert len(juris) >= 1

    def test_favorabilidade_calculation(self):
        p = _make_processo()
        p.area = "consumidor"
        result = self.agent.execute(p)
        juris_ind = [i for i in result.indicadores_risco if i.categoria == "jurisprudencia"]
        assert len(juris_ind) == 1
        # Consumidor teses have high favorability => low risk score
        assert juris_ind[0].score < 0.5

    def test_indicador_created(self):
        p = _make_processo()
        p.area = "tributaria"
        result = self.agent.execute(p)
        juris_ind = [i for i in result.indicadores_risco if i.categoria == "jurisprudencia"]
        assert len(juris_ind) == 1
        assert juris_ind[0].descricao is not None

    def test_no_duplicate_pontos(self):
        p = _make_processo()
        p.area = "civel"
        # Run twice
        result = self.agent.execute(p)
        result = self.agent.execute(result)
        juris = [a for a in result.pontos_atencao if "JURISPRUDENCIA" in a]
        # Should not duplicate
        assert len(juris) == len(set(juris))


# =========================================================================
# 13. ValidadorConformidade
# =========================================================================

class TestValidadorConformidade:
    def setup_method(self):
        self.agent = ValidadorConformidade()

    def test_prazo_vencido_alert(self):
        p = _make_processo()
        p.prazos = [Prazo(tipo="manifestacao", data_fim="2024-01-01", dias_restantes=-10)]
        result = self.agent.execute(p)
        assert any("vencido" in a.lower() for a in result.pontos_atencao)

    def test_processo_parado_alert(self):
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        p = _make_processo()
        p.data_ultima_movimentacao = old_date
        result = self.agent.execute(p)
        assert any("movimentacao" in a.lower() or "parado" in a.lower() for a in result.pontos_atencao)

    def test_processo_parado_risk_indicator(self):
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        p = _make_processo()
        p.data_ultima_movimentacao = old_date
        result = self.agent.execute(p)
        conf_ind = [i for i in result.indicadores_risco if i.categoria == "conformidade"]
        assert len(conf_ind) >= 1

    def test_sigilo_alert(self):
        p = _make_processo()
        p.nivel_sigilo = 3
        result = self.agent.execute(p)
        assert any("sigilo" in a.lower() for a in result.pontos_atencao)

    def test_data_consistency_no_classe(self):
        p = _make_processo()
        p.movimentacoes = [Movimentacao(nome="Despacho", data="2024-01-01")]
        p.classe_processual = None
        result = self.agent.execute(p)
        assert any("classe processual" in a.lower() for a in result.pontos_atencao)

    def test_data_consistency_comunicacoes_no_partes(self):
        p = _make_processo()
        p.comunicacoes = [
            Comunicacao(tipo="Intimacao", data_disponibilizacao="2024-01-01")
        ]
        p.partes = []
        result = self.agent.execute(p)
        assert any("partes" in a.lower() for a in result.pontos_atencao)

    def test_no_alerts_clean_process(self):
        p = _make_processo()
        result = self.agent.execute(p)
        # Should not have conformidade alerts for a clean process
        conf_alerts = [a for a in result.pontos_atencao if "CONFORMIDADE" in a]
        assert len(conf_alerts) == 0


# =========================================================================
# 14. PrevisorResultado
# =========================================================================

class TestPrevisorResultado:
    def setup_method(self):
        self.agent = PrevisorResultado()

    def test_previsao_indicator_created(self):
        p = _make_processo()
        p.risco_score = 0.3
        result = self.agent.execute(p)
        prev_ind = [i for i in result.indicadores_risco if i.categoria == "previsao_resultado"]
        assert len(prev_ind) == 1

    def test_previsao_favoravel(self):
        p = _make_processo()
        p.fase = FaseProcessual.execucao
        p.risco_score = 0.1
        p.duracao_dias = 200
        p.indicadores_risco = [
            IndicadorRisco(categoria="jurisprudencia", nivel=NivelRisco.baixo, score=0.2,
                           descricao="test")
        ]
        result = self.agent.execute(p)
        prev_ind = [i for i in result.indicadores_risco if i.categoria == "previsao_resultado"][0]
        assert "Favoravel" in prev_ind.descricao or "Moderado" in prev_ind.descricao

    def test_previsao_desfavoravel(self):
        p = _make_processo()
        p.fase = FaseProcessual.recursal
        p.risco_score = 0.9
        p.duracao_dias = 3000
        p.total_partes = 15
        p.total_movimentacoes = 200
        p.indicadores_risco = [
            IndicadorRisco(categoria="jurisprudencia", nivel=NivelRisco.alto, score=0.8,
                           descricao="test")
        ]
        result = self.agent.execute(p)
        prev_ind = [i for i in result.indicadores_risco if i.categoria == "previsao_resultado"][0]
        assert "desfavoravel" in prev_ind.descricao.lower() or "Desfavoravel" in prev_ind.descricao

    def test_factor_weighting(self):
        p = _make_processo()
        p.risco_score = 0.5
        result = self.agent.execute(p)
        prev_ind = [i for i in result.indicadores_risco if i.categoria == "previsao_resultado"][0]
        # Should contain factor info in description
        assert "Fatores:" in prev_ind.descricao

    def test_pontos_atencao_added(self):
        p = _make_processo()
        p.risco_score = 0.5
        result = self.agent.execute(p)
        assert any("PREVISAO" in a for a in result.pontos_atencao)

    def test_score_bounds(self):
        p = _make_processo()
        p.risco_score = 0.5
        result = self.agent.execute(p)
        prev_ind = [i for i in result.indicadores_risco if i.categoria == "previsao_resultado"][0]
        assert 0.0 <= prev_ind.score <= 1.0

    def test_complexidade_high(self):
        p = _make_processo()
        p.risco_score = 0.5
        p.total_partes = 12
        p.total_movimentacoes = 150
        result = self.agent.execute(p)
        prev_ind = [i for i in result.indicadores_risco if i.categoria == "previsao_resultado"][0]
        assert "complexidade" in prev_ind.descricao.lower()
