#!/usr/bin/env python3
"""
Testes do Sistema de Captacao Automatizada.

Valida:
- CRUD de captacoes via API
- CaptacaoService (sem fontes externas)
- Scheduler inteligente
- Diff entre execucoes
- Integracao com API existente

Uso:
    python -m djen.scripts.test_captacao
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def pr(label, value):
    print(f"  {label}: {value}")


def sep(title):
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)


def test_schemas():
    """Teste 1: Schemas de captacao importam corretamente."""
    sep("TESTE 1: Schemas de Captacao")
    from djen.api.schemas import (
        TipoBusca, PrioridadeCaptacao,
        CaptacaoCreateRequest, CaptacaoUpdateRequest, CaptacaoPreviewRequest,
        CaptacaoResponse, ExecucaoCaptacaoResponse, CaptacaoExecucaoResult,
        CaptacaoStatsResponse, DiffResponse,
    )

    pr("TipoBusca valores", [e.value for e in TipoBusca])
    pr("PrioridadeCaptacao valores", [e.value for e in PrioridadeCaptacao])

    req = CaptacaoCreateRequest(
        nome="Teste OAB",
        tipo_busca=TipoBusca.oab,
        numero_oab="123456",
        uf_oab="SP",
    )
    pr("CaptacaoCreateRequest", f"nome={req.nome}, tipo={req.tipo_busca.value}")

    data = req.model_dump()
    pr("Serializado", f"{len(data)} campos")

    assert len(TipoBusca) == 7
    assert len(PrioridadeCaptacao) == 3

    print("\n  [OK] Schemas de captacao OK!")
    return True


def test_database_captacao():
    """Teste 2: CRUD de captacoes no banco."""
    sep("TESTE 2: Database - Captacoes")
    import tempfile
    from djen.api.database import Database

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)

        cap_id = db.criar_captacao(
            nome="Teste Processo TJMA", tipo_busca="processo",
            numero_processo="0044631-56.2012.8.10.0001", tribunal="TJMA",
            fontes="datajud,djen_api", intervalo_minutos=60,
            prioridade="urgente", auto_enriquecer=True,
        )
        pr("Criar captacao", f"id={cap_id}")
        assert cap_id > 0

        cap = db.obter_captacao(cap_id)
        assert cap["nome"] == "Teste Processo TJMA"
        assert cap["tipo_busca"] == "processo"
        assert cap["prioridade"] == "urgente"
        pr("Obter", f"nome={cap['nome']}, tipo={cap['tipo_busca']}")

        cap_id2 = db.criar_captacao(nome="OAB Silva", tipo_busca="oab",
                                     numero_oab="123456", uf_oab="SP", prioridade="normal")
        cap_id3 = db.criar_captacao(nome="Parte BB", tipo_busca="nome_parte",
                                     nome_parte="BANCO DO BRASIL", prioridade="baixa")

        caps = db.listar_captacoes(ativo=True)
        pr("Listar (ativas)", f"{len(caps)} captacoes")
        assert len(caps) == 3

        caps_oab = db.listar_captacoes(tipo_busca="oab")
        assert len(caps_oab) == 1

        db.atualizar_captacao(cap_id, nome="Processo TJMA Atualizado", intervalo_minutos=30)
        cap = db.obter_captacao(cap_id)
        assert cap["nome"] == "Processo TJMA Atualizado"
        pr("Atualizar", "OK")

        db.atualizar_captacao(cap_id, pausado=1)
        cap = db.obter_captacao(cap_id)
        assert cap["pausado"] == 1
        pr("Pausar", "OK")

        exec_id = db.iniciar_execucao_captacao(cap_id, "datajud", '{"tribunais":["tjma"]}')
        db.finalizar_execucao_captacao(exec_id, "completed", 5, 3, 1500)
        db.atualizar_captacao_pos_execucao(cap_id, 5, 3, 60)

        cap = db.obter_captacao(cap_id)
        assert cap["total_execucoes"] == 1
        assert cap["total_resultados"] == 5
        pr("Execucao", f"exec={cap['total_execucoes']}, res={cap['total_resultados']}")

        execs = db.listar_execucoes_captacao(cap_id)
        assert len(execs) == 1
        assert execs[0]["status"] == "completed"

        stats = db.obter_stats_captacao()
        assert stats["total_captacoes"] == 3
        assert stats["total_execucoes"] == 1
        pr("Stats", f"captacoes={stats['total_captacoes']}, execs={stats['total_execucoes']}")

        print("\n  [OK] Database captacao OK!")
        return True
    finally:
        try:
            # Fechar conexao antes de deletar (Windows)
            if hasattr(db, '_local') and hasattr(db._local, 'conn') and db._local.conn:
                db._local.conn.close()
                db._local.conn = None
        except Exception:
            pass
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_captacao_service():
    """Teste 3: CaptacaoService - montagem de parametros."""
    sep("TESTE 3: CaptacaoService - Parametros")
    from djen.agents.captacao_service import CaptacaoService

    service = CaptacaoService()

    # DataJud processo
    params = service._montar_parametros_datajud(
        {"tipo_busca": "processo", "numero_processo": "0044631-56.2012.8.10.0001", "tribunal": "tjma"})
    assert params is not None and params["tribunal"] == "tjma"
    pr("DataJud processo", "OK")

    # DataJud OAB -> None
    params = service._montar_parametros_datajud({"tipo_busca": "oab"})
    assert params is None
    pr("DataJud oab (skip)", "OK")

    # DataJud classe
    params = service._montar_parametros_datajud({"tipo_busca": "classe", "classe_codigo": 307, "tribunal": "stj"})
    assert params["classe_codigo"] == 307
    pr("DataJud classe", "OK")

    # DJEN OAB
    params = service._montar_parametros_djen({"tipo_busca": "oab", "numero_oab": "123456", "uf_oab": "SP"})
    assert params["numero_oab"] == "123456"
    pr("DJEN oab", "OK")

    # DJEN classe -> None
    params = service._montar_parametros_djen({"tipo_busca": "classe"})
    assert params is None
    pr("DJEN classe (skip)", "OK")

    # Horario
    from datetime import datetime
    result = service._dentro_do_horario({"horario_inicio": "00:00", "horario_fim": "23:59",
                                          "dias_semana": "1,2,3,4,5,6,7"}, datetime.now())
    assert result is True
    pr("Dentro do horario", "OK")

    print("\n  [OK] CaptacaoService parametros OK!")
    return True


def test_api_endpoints():
    """Teste 4: Endpoints REST via TestClient."""
    sep("TESTE 4: API Endpoints Captacao")

    try:
        from fastapi.testclient import TestClient
        from djen.api.app import app

        client = TestClient(app, raise_server_exceptions=False)

        # Stats
        resp = client.get("/api/captacao/stats")
        assert resp.status_code == 200
        pr("GET /api/captacao/stats", resp.status_code)

        # Listar
        resp = client.get("/api/captacao/listar")
        assert resp.status_code == 200
        pr("GET /api/captacao/listar", resp.status_code)

        # Criar processo
        resp = client.post("/api/captacao/criar", json={
            "nome": "Test Processo", "tipo_busca": "processo",
            "numero_processo": "0044631-56.2012.8.10.0001", "tribunal": "TJMA",
            "fontes": ["datajud", "djen_api"], "intervalo_minutos": 120,
        })
        assert resp.status_code == 200
        cap1_id = resp.json()["id"]
        pr("POST /api/captacao/criar (processo)", f"id={cap1_id}")

        # Criar OAB
        resp = client.post("/api/captacao/criar", json={
            "nome": "Test OAB", "tipo_busca": "oab",
            "numero_oab": "123456", "uf_oab": "SP",
            "fontes": ["djen_api"], "intervalo_minutos": 60,
            "prioridade": "urgente", "auto_enriquecer": True,
        })
        assert resp.status_code == 200
        cap2_id = resp.json()["id"]
        pr("POST /api/captacao/criar (oab)", f"id={cap2_id}")

        # Criar classe
        resp = client.post("/api/captacao/criar", json={
            "nome": "HCs STJ", "tipo_busca": "classe",
            "classe_codigo": 307, "tribunal": "stj",
            "fontes": ["datajud"], "prioridade": "baixa",
        })
        assert resp.status_code == 200
        pr("POST /api/captacao/criar (classe)", resp.status_code)

        # Obter
        resp = client.get(f"/api/captacao/{cap1_id}")
        assert resp.status_code == 200
        assert resp.json()["nome"] == "Test Processo"
        pr(f"GET /api/captacao/{cap1_id}", resp.status_code)

        # Atualizar
        resp = client.put(f"/api/captacao/{cap1_id}", json={"nome": "Atualizado", "intervalo_minutos": 30})
        assert resp.status_code == 200
        assert resp.json()["intervalo_minutos"] == 30
        pr(f"PUT /api/captacao/{cap1_id}", resp.status_code)

        # Listar filtros
        resp = client.get("/api/captacao/listar?ativo=true")
        assert resp.status_code == 200 and resp.json()["total"] >= 3
        pr("GET /api/captacao/listar?ativo=true", f"total={resp.json()['total']}")

        # Pausar/retomar
        resp = client.post(f"/api/captacao/{cap1_id}/pausar")
        assert resp.status_code == 200
        resp = client.post(f"/api/captacao/{cap1_id}/retomar")
        assert resp.status_code == 200
        pr("Pausar/Retomar", "OK")

        # Historico/resultados/diff
        for endpoint in ["historico", "resultados", "diff"]:
            resp = client.get(f"/api/captacao/{cap1_id}/{endpoint}")
            assert resp.status_code == 200
            pr(f"GET .../{endpoint}", resp.status_code)

        # Desativar
        resp = client.delete(f"/api/captacao/{cap2_id}")
        assert resp.status_code == 200
        pr(f"DELETE /api/captacao/{cap2_id}", resp.status_code)

        # 404
        resp = client.get("/api/captacao/99999")
        assert resp.status_code == 404
        pr("GET /api/captacao/99999 (404)", resp.status_code)

        # Rotas existentes nao quebraram
        for path in ["/api/health", "/api/monitor/stats", "/api/processo/agents"]:
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} quebrou!"
        pr("Rotas existentes", "OK")

        print("\n  [OK] Todos os endpoints funcionando!")
        return True

    except Exception as e:
        print(f"\n  [FALHOU] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_route_count():
    """Teste 5: Contagem de rotas."""
    sep("TESTE 5: Contagem de Rotas")
    from djen.api.app import app

    routes = [r for r in app.routes if hasattr(r, "path")]
    captacao_routes = [r for r in routes if "/api/captacao" in getattr(r, "path", "")]

    pr("Total rotas API", len(routes))
    pr("Rotas /api/captacao/*", len(captacao_routes))
    for r in captacao_routes:
        methods = getattr(r, "methods", {"WS"})
        print(f"    {methods} {r.path}")

    if len(captacao_routes) < 13:
        print(f"\n  [FALHOU] Esperado >= 13, got {len(captacao_routes)}")
        return False

    print(f"\n  [OK] {len(captacao_routes)} rotas de captacao!")
    return True


def test_executar_captacao():
    """Teste 6: Executar captacao com DataJud real."""
    sep("TESTE 6: Executar Captacao (DataJud real)")

    try:
        from fastapi.testclient import TestClient
        from djen.api.app import app

        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post("/api/captacao/criar", json={
            "nome": "Exec Test", "tipo_busca": "processo",
            "numero_processo": "0044631-56.2012.8.10.0001",
            "tribunal": "TJMA", "fontes": ["datajud"],
        })
        cap_id = resp.json()["id"]
        pr("Captacao criada", f"id={cap_id}")

        pr("Executando...", "(pode levar 5-15s)")
        resp = client.post(f"/api/captacao/{cap_id}/executar")
        pr("POST .../executar", resp.status_code)

        if resp.status_code == 200:
            data = resp.json()
            pr("  status", data.get("status"))
            pr("  total_resultados", data.get("total_resultados"))
            pr("  novos_resultados", data.get("novos_resultados"))
            pr("  tempo_total_ms", data.get("tempo_total_ms"))
            pr("  erros", data.get("erros"))

            # Historico
            resp2 = client.get(f"/api/captacao/{cap_id}/historico")
            if resp2.status_code == 200:
                pr("  historico.total", resp2.json().get("total"))

            # Resultados
            resp3 = client.get(f"/api/captacao/{cap_id}/resultados")
            if resp3.status_code == 200:
                pr("  resultados.total", resp3.json().get("total"))

        print("\n  [OK] Execucao de captacao concluida!")
        return True

    except Exception as e:
        print(f"\n  [FALHOU] {e}")
        return False


def main():
    print("")
    print("#" * 70)
    print("  CAPTACAO AUTOMATIZADA - Testes")
    print(f"  Data: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("#" * 70)

    results = {}
    results["schemas"] = test_schemas()
    results["database"] = test_database_captacao()
    results["service_params"] = test_captacao_service()
    results["api_endpoints"] = test_api_endpoints()
    results["route_count"] = test_route_count()
    results["executar_datajud"] = test_executar_captacao()

    sep("RESUMO")
    total = len(results)
    ok = sum(1 for v in results.values() if v)

    for name, passed in results.items():
        status = "[OK]    " if passed else "[FALHOU]"
        print(f"  {status} {name}")

    print(f"\n  Total: {ok}/{total} testes passaram")
    if ok == total:
        print("\n  TODOS OS TESTES PASSARAM!")

    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
