"""
Tests for ResultadoRepository - SQLite persistence for ProcessoCanonical.
"""

import os
import pytest

from djen.api.database import Database
from djen.api.resultado_repository import ResultadoRepository
from djen.agents.canonical_model import (
    ProcessoCanonical,
    NivelRisco,
    StatusProcesso,
    FaseProcessual,
    ParteProcessual,
    Advogado,
    Movimentacao,
    Comunicacao,
    PoloProcessual,
    TipoParte,
)


@pytest.fixture
def repo(tmp_path):
    """Create a ResultadoRepository backed by a temporary SQLite database."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path=db_path)
    return ResultadoRepository(db)


def _make_processo(
    numero: str = "0000001-00.2024.8.26.0100",
    tribunal: str = "TJSP",
    area: str = "civel",
    risco: NivelRisco = NivelRisco.medio,
    risco_score: float = 0.5,
    resumo: str = "Resumo do processo de teste.",
    status: StatusProcesso = StatusProcesso.ativo,
    fase: FaseProcessual = FaseProcessual.conhecimento,
    valor_causa: float = 10000.0,
    total_mov: int = 5,
    total_com: int = 2,
    processing_time_ms: int = 1200,
    **kwargs,
) -> ProcessoCanonical:
    return ProcessoCanonical(
        numero_processo=numero,
        tribunal=tribunal,
        area=area,
        risco_geral=risco,
        risco_score=risco_score,
        resumo_executivo=resumo,
        status=status,
        fase=fase,
        valor_causa=valor_causa,
        total_movimentacoes=total_mov,
        total_comunicacoes=total_com,
        processing_time_ms=processing_time_ms,
        **kwargs,
    )


# -----------------------------------------------------------------------
# 1. Table creation
# -----------------------------------------------------------------------
class TestTableCreation:
    def test_table_exists(self, repo):
        row = repo.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='resultados_analise'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "resultados_analise"


# -----------------------------------------------------------------------
# 2. Save and retrieve
# -----------------------------------------------------------------------
class TestSaveAndRetrieve:
    def test_save_and_obter(self, repo):
        p = _make_processo()
        row_id = repo.salvar(p)
        assert row_id > 0

        loaded = repo.obter(p.numero_processo)
        assert loaded is not None
        assert loaded.numero_processo == p.numero_processo
        assert loaded.tribunal == p.tribunal


# -----------------------------------------------------------------------
# 3. Upsert
# -----------------------------------------------------------------------
class TestUpsert:
    def test_upsert_updates_existing(self, repo):
        p1 = _make_processo(resumo="Versao 1")
        id1 = repo.salvar(p1)

        p2 = _make_processo(resumo="Versao 2", risco_score=0.9)
        id2 = repo.salvar(p2)

        # Should be same row
        assert id2 == id1

        loaded = repo.obter(p1.numero_processo)
        assert loaded.resumo_executivo == "Versao 2"
        assert loaded.risco_score == 0.9

        # Only one row in the table
        count = repo.db.conn.execute(
            "SELECT COUNT(*) as c FROM resultados_analise"
        ).fetchone()["c"]
        assert count == 1


# -----------------------------------------------------------------------
# 4. List with pagination
# -----------------------------------------------------------------------
class TestListPagination:
    def test_limit_offset(self, repo):
        for i in range(5):
            repo.salvar(_make_processo(numero=f"000000{i}-00.2024.8.26.0100"))

        result = repo.listar(limit=2, offset=0)
        assert result["total"] == 5
        assert len(result["resultados"]) == 2

        result2 = repo.listar(limit=2, offset=2)
        assert len(result2["resultados"]) == 2

        result3 = repo.listar(limit=2, offset=4)
        assert len(result3["resultados"]) == 1


# -----------------------------------------------------------------------
# 5. List with filters
# -----------------------------------------------------------------------
class TestListFilters:
    def test_filter_tribunal(self, repo):
        repo.salvar(_make_processo(numero="001", tribunal="TJSP"))
        repo.salvar(_make_processo(numero="002", tribunal="TJRJ"))
        repo.salvar(_make_processo(numero="003", tribunal="TJSP"))

        result = repo.listar(tribunal="TJSP")
        assert result["total"] == 2

    def test_filter_area(self, repo):
        repo.salvar(_make_processo(numero="001", area="civel"))
        repo.salvar(_make_processo(numero="002", area="criminal"))

        result = repo.listar(area="civel")
        assert result["total"] == 1
        assert result["resultados"][0]["area"] == "civel"

    def test_filter_risco(self, repo):
        repo.salvar(_make_processo(numero="001", risco=NivelRisco.alto))
        repo.salvar(_make_processo(numero="002", risco=NivelRisco.baixo))
        repo.salvar(_make_processo(numero="003", risco=NivelRisco.alto))

        result = repo.listar(risco="alto")
        assert result["total"] == 2


# -----------------------------------------------------------------------
# 6. Delete
# -----------------------------------------------------------------------
class TestDelete:
    def test_delete_existing(self, repo):
        p = _make_processo()
        repo.salvar(p)

        assert repo.deletar(p.numero_processo) is True
        assert repo.obter(p.numero_processo) is None

    def test_delete_nonexistent(self, repo):
        assert repo.deletar("inexistente") is False


# -----------------------------------------------------------------------
# 7. Stats
# -----------------------------------------------------------------------
class TestStats:
    def test_stats_counts(self, repo):
        repo.salvar(_make_processo(numero="001", risco=NivelRisco.alto, tribunal="TJSP", area="civel", risco_score=0.8))
        repo.salvar(_make_processo(numero="002", risco=NivelRisco.baixo, tribunal="TJRJ", area="criminal", risco_score=0.2))
        repo.salvar(_make_processo(numero="003", risco=NivelRisco.alto, tribunal="TJSP", area="civel", risco_score=0.9))

        s = repo.stats()
        assert s["total_resultados"] == 3
        assert s["por_risco"]["alto"] == 2
        assert s["por_risco"]["baixo"] == 1
        assert s["por_tribunal"]["TJSP"] == 2
        assert s["por_tribunal"]["TJRJ"] == 1
        assert s["por_area"]["civel"] == 2
        assert s["por_area"]["criminal"] == 1
        # avg of 0.8, 0.2, 0.9 = 0.633
        assert 0.6 <= s["risco_score_medio"] <= 0.67
        assert s["primeiro_registro"] is not None
        assert s["ultimo_registro"] is not None

    def test_stats_empty(self, repo):
        s = repo.stats()
        assert s["total_resultados"] == 0
        assert s["risco_score_medio"] == 0.0


# -----------------------------------------------------------------------
# 8. Full-text search in resumo_executivo
# -----------------------------------------------------------------------
class TestFullTextSearch:
    def test_buscar_texto(self, repo):
        repo.salvar(_make_processo(numero="001", resumo="Acao de cobranca com alto risco"))
        repo.salvar(_make_processo(numero="002", resumo="Processo trabalhista sem risco"))
        repo.salvar(_make_processo(numero="003", resumo="Demanda civel ordinaria"))

        results = repo.buscar_texto("risco")
        assert len(results) == 2

        results2 = repo.buscar_texto("trabalhista")
        assert len(results2) == 1
        assert results2[0]["numero_processo"] == "002"

    def test_buscar_texto_sem_resultado(self, repo):
        repo.salvar(_make_processo(numero="001", resumo="Acao de cobranca"))
        results = repo.buscar_texto("xyz_nao_existe")
        assert len(results) == 0


# -----------------------------------------------------------------------
# 9. Serialization/deserialization integrity
# -----------------------------------------------------------------------
class TestSerializationIntegrity:
    def test_all_fields_preserved(self, repo):
        p = _make_processo(
            numero="999-99.2024.8.26.0100",
            tribunal="TJMG",
            area="trabalhista",
            risco=NivelRisco.critico,
            risco_score=0.95,
            resumo="Resumo completo para teste de integridade",
            status=StatusProcesso.suspenso,
            fase=FaseProcessual.recursal,
            valor_causa=55000.50,
            total_mov=12,
            total_com=7,
            processing_time_ms=3400,
            grau="G2",
            classe_processual="Recurso Ordinario",
            assuntos=["Horas Extras", "Adicional Noturno"],
            orgao_julgador="2a Turma",
            uf="MG",
            pontos_atencao=["Prazo recursal proximo", "Valor elevado"],
            proximos_passos=["Preparar contrarrazoes"],
            partes=[
                ParteProcessual(
                    nome="Empresa XYZ Ltda",
                    tipo=TipoParte.pessoa_juridica,
                    polo=PoloProcessual.passivo,
                    advogados=[Advogado(nome="Dr. Fulano", oab="12345", uf_oab="MG")],
                )
            ],
            movimentacoes=[
                Movimentacao(nome="Distribuicao", data="2024-01-10"),
                Movimentacao(nome="Despacho", data="2024-02-15", complemento="Cite-se"),
            ],
            comunicacoes=[
                Comunicacao(tipo="Intimacao", data_disponibilizacao="2024-03-01", texto="Intimar parte")
            ],
        )

        repo.salvar(p)
        loaded = repo.obter(p.numero_processo)

        assert loaded is not None
        assert loaded.numero_processo == p.numero_processo
        assert loaded.tribunal == p.tribunal
        assert loaded.area == p.area
        assert loaded.risco_geral == p.risco_geral
        assert loaded.risco_score == p.risco_score
        assert loaded.resumo_executivo == p.resumo_executivo
        assert loaded.status == p.status
        assert loaded.fase == p.fase
        assert loaded.valor_causa == p.valor_causa
        assert loaded.total_movimentacoes == p.total_movimentacoes
        assert loaded.total_comunicacoes == p.total_comunicacoes
        assert loaded.processing_time_ms == p.processing_time_ms
        assert loaded.grau == p.grau
        assert loaded.classe_processual == p.classe_processual
        assert loaded.assuntos == p.assuntos
        assert loaded.orgao_julgador == p.orgao_julgador
        assert loaded.uf == p.uf
        assert loaded.pontos_atencao == p.pontos_atencao
        assert loaded.proximos_passos == p.proximos_passos
        assert len(loaded.partes) == 1
        assert loaded.partes[0].nome == "Empresa XYZ Ltda"
        assert loaded.partes[0].advogados[0].oab == "12345"
        assert len(loaded.movimentacoes) == 2
        assert loaded.movimentacoes[1].complemento == "Cite-se"
        assert len(loaded.comunicacoes) == 1
        assert loaded.comunicacoes[0].tipo == "Intimacao"


# -----------------------------------------------------------------------
# 10. Empty database
# -----------------------------------------------------------------------
class TestEmptyDatabase:
    def test_listar_empty(self, repo):
        result = repo.listar()
        assert result["total"] == 0
        assert result["resultados"] == []

    def test_buscar_texto_empty(self, repo):
        assert repo.buscar_texto("qualquer") == []


# -----------------------------------------------------------------------
# 11. Obter non-existent
# -----------------------------------------------------------------------
class TestObterNonExistent:
    def test_returns_none(self, repo):
        assert repo.obter("inexistente-123") is None


# -----------------------------------------------------------------------
# 12. Multiple processos
# -----------------------------------------------------------------------
class TestMultipleProcessos:
    def test_store_and_retrieve_multiple(self, repo):
        processos = [
            _make_processo(numero=f"proc-{i}", tribunal=f"TJ{i}", area="civel", risco_score=i * 0.1)
            for i in range(1, 6)
        ]
        ids = []
        for p in processos:
            ids.append(repo.salvar(p))

        # All IDs are unique
        assert len(set(ids)) == 5

        # Each can be retrieved
        for p in processos:
            loaded = repo.obter(p.numero_processo)
            assert loaded is not None
            assert loaded.numero_processo == p.numero_processo

        # List returns all
        result = repo.listar(limit=100)
        assert result["total"] == 5
        assert len(result["resultados"]) == 5
