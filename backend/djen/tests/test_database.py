"""
Tests for djen/api/database.py - Database layer.
"""

import os
import sqlite3
import threading
import pytest

from djen.api.database import Database


@pytest.fixture
def db(tmp_path):
    """Create a fresh Database instance using a temporary directory."""
    db_path = os.path.join(str(tmp_path), "data", "test.db")
    return Database(db_path=db_path)


# --- 1. Initialization ---

def test_init_creates_file_and_tables(tmp_path):
    db_path = os.path.join(str(tmp_path), "subdir", "test.db")
    db = Database(db_path=db_path)
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    for t in ("monitorados", "publicacoes", "buscas", "health_checks"):
        assert t in tables


# --- 2-3. adicionar_monitorado ---

def test_adicionar_monitorado_creates_and_returns_id(db):
    mid = db.adicionar_monitorado("oab", "12345/SP", nome_amigavel="Joao")
    assert isinstance(mid, int)
    assert mid > 0


def test_adicionar_monitorado_duplicate_reactivates(db):
    mid1 = db.adicionar_monitorado("oab", "99999/RJ")
    db.desativar_monitorado(mid1)
    row = db.obter_monitorado(mid1)
    assert row["ativo"] == 0

    mid2 = db.adicionar_monitorado("oab", "99999/RJ")
    assert mid2 == mid1
    row = db.obter_monitorado(mid1)
    assert row["ativo"] == 1


# --- 4-5. listar_monitorados ---

def test_listar_monitorados_returns_active(db):
    db.adicionar_monitorado("oab", "111/SP")
    mid2 = db.adicionar_monitorado("oab", "222/SP")
    db.desativar_monitorado(mid2)

    ativos = db.listar_monitorados()
    assert len(ativos) == 1
    assert ativos[0]["valor"] == "111/SP"


def test_listar_monitorados_includes_inactive(db):
    db.adicionar_monitorado("oab", "111/SP")
    mid2 = db.adicionar_monitorado("oab", "222/SP")
    db.desativar_monitorado(mid2)

    todos = db.listar_monitorados(apenas_ativos=False)
    assert len(todos) == 2


# --- 6-7. obter_monitorado ---

def test_obter_monitorado_returns_correct(db):
    mid = db.adicionar_monitorado("cnpj", "00.000.000/0001-00", nome_amigavel="Empresa X", tribunal="TJSP")
    row = db.obter_monitorado(mid)
    assert row is not None
    assert row["tipo"] == "cnpj"
    assert row["valor"] == "00.000.000/0001-00"
    assert row["nome_amigavel"] == "Empresa X"
    assert row["tribunal"] == "TJSP"
    assert row["ativo"] == 1


def test_obter_monitorado_nonexistent(db):
    assert db.obter_monitorado(9999) is None


# --- 8. atualizar_monitorado ---

def test_atualizar_monitorado_changes_fields(db):
    mid = db.adicionar_monitorado("oab", "555/MG", nome_amigavel="Old")
    result = db.atualizar_monitorado(mid, nome_amigavel="New", tribunal="TJMG")
    assert result is True
    row = db.obter_monitorado(mid)
    assert row["nome_amigavel"] == "New"
    assert row["tribunal"] == "TJMG"


def test_atualizar_monitorado_no_valid_fields(db):
    mid = db.adicionar_monitorado("oab", "666/MG")
    result = db.atualizar_monitorado(mid, invalid_field="value")
    assert result is False


# --- 9. desativar_monitorado ---

def test_desativar_monitorado(db):
    mid = db.adicionar_monitorado("oab", "777/RJ")
    db.desativar_monitorado(mid)
    row = db.obter_monitorado(mid)
    assert row["ativo"] == 0


# --- 10-11. salvar_publicacao ---

def _make_pub(hash_val="h1", fonte="datajud", tribunal="TJSP", processo="0001234"):
    return {
        "hash": hash_val,
        "fonte": fonte,
        "tribunal": tribunal,
        "data_publicacao": "2024-01-01",
        "conteudo": "Texto da publicacao",
        "numero_processo": processo,
    }


def test_salvar_publicacao_creates_entry(db):
    mid = db.adicionar_monitorado("oab", "100/SP")
    pid = db.salvar_publicacao(_make_pub(), monitorado_id=mid)
    assert pid is not None
    assert pid > 0


def test_salvar_publicacao_duplicate_hash_ignored(db):
    db.salvar_publicacao(_make_pub(hash_val="dup1"))
    pid2 = db.salvar_publicacao(_make_pub(hash_val="dup1"))
    # INSERT OR IGNORE returns 0 for lastrowid when ignored
    # The method returns None or 0 for ignored rows
    pubs = db.buscar_publicacoes()
    assert len(pubs) == 1


# --- 12-16. buscar_publicacoes ---

def _seed_publications(db):
    db.salvar_publicacao(_make_pub("h1", "datajud", "TJSP", "111"))
    db.salvar_publicacao(_make_pub("h2", "datajud", "TJRJ", "222"))
    db.salvar_publicacao(_make_pub("h3", "djen_api", "TJSP", "333"))
    db.salvar_publicacao(_make_pub("h4", "djen_api", "TJMG", "444"))
    db.salvar_publicacao(_make_pub("h5", "datajud", "TJSP", "555"))


def test_buscar_publicacoes_returns_all(db):
    _seed_publications(db)
    pubs = db.buscar_publicacoes(limite=100)
    assert len(pubs) == 5


def test_buscar_publicacoes_filter_fonte(db):
    _seed_publications(db)
    pubs = db.buscar_publicacoes(fonte="datajud", limite=100)
    assert len(pubs) == 3
    assert all(p["fonte"] == "datajud" for p in pubs)


def test_buscar_publicacoes_filter_tribunal(db):
    _seed_publications(db)
    pubs = db.buscar_publicacoes(tribunal="TJSP", limite=100)
    assert len(pubs) == 3
    assert all(p["tribunal"] == "TJSP" for p in pubs)


def test_buscar_publicacoes_filter_processo(db):
    _seed_publications(db)
    pubs = db.buscar_publicacoes(processo="333", limite=100)
    assert len(pubs) == 1
    assert pubs[0]["numero_processo"] == "333"


def test_buscar_publicacoes_pagination(db):
    _seed_publications(db)
    page1 = db.buscar_publicacoes(limite=2, offset=0)
    page2 = db.buscar_publicacoes(limite=2, offset=2)
    page3 = db.buscar_publicacoes(limite=2, offset=4)
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
    all_ids = [p["id"] for p in page1 + page2 + page3]
    assert len(set(all_ids)) == 5  # no duplicates


# --- 17. registrar_busca ---

def test_registrar_busca(db):
    bid = db.registrar_busca("oab", "datajud", "TJSP", "12345", 10, "ok", 150)
    assert isinstance(bid, int)
    assert bid > 0


# --- 18. registrar_health ---

def test_registrar_health(db):
    hid = db.registrar_health("datajud", "ok", latency_ms=200, message="All good", proxy_used=True)
    assert isinstance(hid, int)
    assert hid > 0


# --- 19. obter_stats ---

def test_obter_stats(db):
    db.adicionar_monitorado("oab", "aaa/SP")
    db.adicionar_monitorado("oab", "bbb/SP")
    mid3 = db.adicionar_monitorado("oab", "ccc/SP")
    db.desativar_monitorado(mid3)

    db.salvar_publicacao(_make_pub("s1"))
    db.salvar_publicacao(_make_pub("s2", processo="xyz"))

    db.registrar_busca("oab", "datajud", None, "aaa", 1)

    stats = db.obter_stats()
    assert stats["total_monitorados"] == 3
    assert stats["monitorados_ativos"] == 2
    assert stats["total_publicacoes"] == 2
    assert stats["total_buscas"] == 1


# --- 20. Thread safety ---

def test_thread_safety_wal_mode(db):
    row = db.conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0].lower() == "wal"


def test_thread_safety_concurrent_access(tmp_path):
    db_path = os.path.join(str(tmp_path), "data", "concurrent.db")
    db = Database(db_path=db_path)
    errors = []

    def worker(thread_id):
        try:
            # Each thread gets its own connection via thread-local
            db.adicionar_monitorado("oab", f"t{thread_id}/SP", nome_amigavel=f"Thread {thread_id}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    todos = db.listar_monitorados(apenas_ativos=False)
    assert len(todos) == 10
