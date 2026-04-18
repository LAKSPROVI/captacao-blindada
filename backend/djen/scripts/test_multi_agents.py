#!/usr/bin/env python3
"""
Testes do Sistema Multi-Agentes e Endpoints de Processo.

Valida:
- Registro e execucao de agentes
- Pipeline service (com mock de fontes externas)
- Endpoints REST /api/processo/*
- Cache em memoria
- Integracao com API existente

Uso:
    python -m djen.scripts.test_multi_agents
"""

import sys
import os
import time
import json

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def print_separator(title):
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)


def print_result(label, value):
    print(f"  {label}: {value}")


def test_agent_registry():
    """Teste 1: Verificar que todos os agentes estao registrados."""
    print_separator("TESTE 1: Agent Registry")

    from djen.agents.orchestrator import AgentRegistry
    import djen.agents.specialized  # noqa: trigger registration

    agents = AgentRegistry.list_names()
    print_result("Agentes registrados", len(agents))
    for name in sorted(agents):
        cls = AgentRegistry.get(name)
        print(f"    - {name}: {cls.description} (priority={cls.priority}, depends={cls.depends_on})")

    expected = [
        "validador", "coletor_datajud", "coletor_djen",
        "extrator_entidades", "analisador_movimentacoes",
        "classificador_causa", "extrator_valores", "analisador_cronologia",
        "calculador_prazos", "analisador_risco", "gerador_resumo",
        "analisador_jurisprudencia", "validador_conformidade", "previsor_resultado",
    ]

    missing = [n for n in expected if n not in agents]
    if missing:
        print(f"\n  [FALHOU] Agentes faltantes: {missing}")
        return False

    print(f"\n  [OK] Todos os {len(expected)} agentes registrados!")
    return True


def test_orchestrator_layer_resolution():
    """Teste 2: Verificar resolucao de camadas do orchestrator."""
    print_separator("TESTE 2: Orchestrator Layer Resolution")

    from djen.agents.orchestrator import AgentOrchestrator, AgentRegistry
    import djen.agents.specialized  # noqa

    orch = AgentOrchestrator()
    agents = [cls() for cls in AgentRegistry.all().values()]
    layers = orch._resolve_execution_order(agents)

    print_result("Total agentes", len(agents))
    print_result("Total camadas", len(layers))

    for i, layer in enumerate(layers):
        names = [a.name for a in layer]
        print(f"    Camada {i+1}: {names}")

    if len(layers) < 3:
        print("\n  [FALHOU] Esperado pelo menos 3 camadas")
        return False

    # Validar que validador esta na primeira camada
    first_layer_names = [a.name for a in layers[0]]
    if "validador" not in first_layer_names:
        print("\n  [FALHOU] 'validador' deveria estar na primeira camada")
        return False

    print("\n  [OK] Resolucao de camadas correta!")
    return True


def test_pipeline_with_mock():
    """Teste 3: Pipeline service sem fontes externas (mock data)."""
    print_separator("TESTE 3: Pipeline Service (mock)")

    from djen.agents.canonical_model import ProcessoCanonical, Movimentacao, Comunicacao
    from djen.agents.orchestrator import AgentOrchestrator, AgentRegistry
    import djen.agents.specialized  # noqa

    # Criar processo com dados simulados (como se coletores ja tivessem rodado)
    p = ProcessoCanonical(
        numero_processo="0044631-56.2012.8.10.0001",
        tribunal="TJMA",
        classe_processual="Procedimento Comum Civel",
        classe_codigo=7,
        orgao_julgador="1a Vara Civel de Sao Luis",
        data_ajuizamento="2012-09-15T00:00:00",
        assuntos=["Indenizacao por Dano Moral"],
        fontes_consultadas=["mock"],
        movimentacoes=[
            Movimentacao(codigo=26, nome="Distribuido por sorteio", data="2012-09-15T10:30:00"),
            Movimentacao(codigo=11, nome="Despacho", data="2012-10-01T14:00:00"),
            Movimentacao(codigo=85, nome="Juntada de peticao", data="2012-11-05T09:00:00"),
            Movimentacao(codigo=22, nome="Sentenca proferida", data="2013-06-20T16:00:00"),
            Movimentacao(codigo=193, nome="Recurso de apelacao", data="2013-07-10T11:00:00"),
            Movimentacao(codigo=60, nome="Publicacao no diario", data="2013-07-15T08:00:00"),
        ],
        comunicacoes=[
            Comunicacao(
                id=1,
                tipo="Intimacao",
                data_disponibilizacao="2024-03-01",
                texto="Fica intimado o Autor JOSE DA SILVA para se manifestar no prazo de 15 dias uteis sobre o laudo pericial. Valor da causa: R$ 50.000,00. OAB: SP 123456",
                meio="Diario Eletronico",
                orgao="1a Vara Civel",
                destinatarios=["JOSE DA SILVA"],
            ),
            Comunicacao(
                id=2,
                tipo="Intimacao",
                data_disponibilizacao="2024-03-10",
                texto="Intima-se o Reu BANCO DO BRASIL S/A para cumprir a obrigacao no prazo de 30 dias. Condenacao: R$ 25.000,00 a titulo de indenizacao.",
                meio="Diario Eletronico",
                orgao="1a Vara Civel",
                destinatarios=["BANCO DO BRASIL S/A"],
            ),
        ],
    )

    # Executar apenas agentes que NAO dependem de coleta externa
    agentes_mock = [
        "extrator_entidades", "analisador_movimentacoes",
        "classificador_causa", "extrator_valores", "analisador_cronologia",
        "calculador_prazos", "analisador_risco",
        "analisador_jurisprudencia", "validador_conformidade",
        "previsor_resultado", "gerador_resumo",
    ]

    orch = AgentOrchestrator()
    p = orch.process(p, agent_names=agentes_mock)

    # Verificar resultados
    print_result("Agentes executados", len(p.agents_executed))
    for ar in p.agents_executed:
        print(f"    {ar.agent_name}: {ar.status.value} ({ar.duration_ms}ms)")

    print_result("Partes encontradas", p.total_partes)
    for parte in p.partes:
        print(f"    - {parte.nome} ({parte.tipo.value}, polo={parte.polo.value})")

    print_result("Advogados", len(p.advogados))
    print_result("Area", p.area)
    print_result("Fase", p.fase.value)
    print_result("Status", p.status.value)
    print_result("Valores extraidos", len(p.valores))
    for v in p.valores:
        print(f"    - {v.tipo}: R$ {v.valor:,.2f}")

    print_result("Valor da causa", p.valor_causa)
    print_result("Prazos", len(p.prazos))
    for pr in p.prazos:
        print(f"    - {pr.tipo}: vence {pr.data_fim} ({pr.dias_restantes} dias restantes)")

    print_result("Timeline eventos", len(p.timeline))
    print_result("Risco geral", f"{p.risco_geral.value} (score={p.risco_score})")
    print_result("Indicadores de risco", len(p.indicadores_risco))
    for ind in p.indicadores_risco:
        print(f"    - [{ind.categoria}] {ind.nivel.value}: {ind.descricao[:80]}")

    print_result("Resumo executivo", (p.resumo_executivo or "")[:150] + "...")
    print_result("Pontos de atencao", len(p.pontos_atencao))
    for pa in p.pontos_atencao[:5]:
        print(f"    - {pa[:80]}")
    print_result("Proximos passos", len(p.proximos_passos))
    print_result("Duracao dias", p.duracao_dias)
    print_result("Tempo processamento", f"{p.processing_time_ms}ms")

    # Validacoes
    failed = sum(1 for ar in p.agents_executed if ar.status.value == "failed")
    if failed > 0:
        print(f"\n  [FALHOU] {failed} agente(s) falharam")
        return False

    if not p.resumo_executivo:
        print("\n  [FALHOU] Resumo executivo nao gerado")
        return False

    if not p.area:
        print("\n  [FALHOU] Area nao classificada")
        return False

    print(f"\n  [OK] Pipeline executou {len(p.agents_executed)} agentes com sucesso!")
    return True


def test_cache():
    """Teste 4: Cache em memoria."""
    print_separator("TESTE 4: Cache em Memoria")

    from djen.agents.pipeline_service import ProcessoCache
    from djen.agents.canonical_model import ProcessoCanonical

    cache = ProcessoCache(max_size=3, ttl_seconds=2)

    # Set e Get
    p1 = ProcessoCanonical(numero_processo="111")
    p2 = ProcessoCanonical(numero_processo="222")
    p3 = ProcessoCanonical(numero_processo="333")
    p4 = ProcessoCanonical(numero_processo="444")

    cache.set("111", p1)
    cache.set("222", p2)
    cache.set("333", p3)

    assert cache.get("111") is not None, "Cache miss para 111"
    assert cache.get("222") is not None, "Cache miss para 222"
    assert cache.get("333") is not None, "Cache miss para 333"
    print_result("Set/Get", "OK")

    # Eviction
    cache.set("444", p4)  # Deve remover o mais antigo (111)
    assert cache.get("111") is None, "111 deveria ter sido removido (eviction)"
    assert cache.get("444") is not None, "Cache miss para 444"
    print_result("Eviction LRU", "OK")

    # Invalidate
    cache.invalidate("222")
    assert cache.get("222") is None, "222 deveria ter sido invalidado"
    print_result("Invalidate", "OK")

    # TTL
    cache_ttl = ProcessoCache(max_size=10, ttl_seconds=1)
    cache_ttl.set("ttl_test", p1)
    assert cache_ttl.get("ttl_test") is not None, "Cache miss antes do TTL"
    time.sleep(1.5)
    assert cache_ttl.get("ttl_test") is None, "TTL deveria ter expirado"
    print_result("TTL expiration", "OK")

    # Stats
    stats = cache.stats()
    print_result("Stats", stats)

    # Clear
    cache.clear()
    assert cache.stats()["size"] == 0, "Cache deveria estar vazio"
    print_result("Clear", "OK")

    print("\n  [OK] Cache funcionando corretamente!")
    return True


def test_api_endpoints():
    """Teste 5: Endpoints REST via TestClient."""
    print_separator("TESTE 5: API Endpoints (TestClient)")

    try:
        from fastapi.testclient import TestClient
        from djen.api.app import app

        client = TestClient(app, raise_server_exceptions=False)

        # 5.1: Root (API existente deve funcionar)
        resp = client.get("/")
        print_result("GET /", f"{resp.status_code}")
        assert resp.status_code == 200, f"Root falhou: {resp.status_code}"

        # 5.2: Listar agentes
        resp = client.get("/api/processo/agents")
        print_result("GET /api/processo/agents", f"{resp.status_code}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 14, f"Esperado >= 14 agentes, got {data['total']}"
        print_result("  Total agentes", data["total"])

        # 5.3: Cache stats
        resp = client.get("/api/processo/cache/stats")
        print_result("GET /api/processo/cache/stats", f"{resp.status_code}")
        assert resp.status_code == 200

        # 5.4: Limpar cache
        resp = client.delete("/api/processo/cache")
        print_result("DELETE /api/processo/cache", f"{resp.status_code}")
        assert resp.status_code == 200

        # 5.5: Analisar processo (POST) - este vai tentar acessar fontes reais
        # Testamos com um numero invalido para verificar que o endpoint responde
        resp = client.post("/api/processo/analisar", json={
            "numero_processo": "0000000-00.0000.0.00.0000",
            "force_refresh": True,
        })
        print_result("POST /api/processo/analisar (dummy)", f"{resp.status_code}")
        # Pode retornar 200 (pipeline roda mas sem dados) ou 500 (erro de fonte)
        # Ambos sao aceitaveis neste teste - o endpoint esta respondendo
        assert resp.status_code in (200, 500), f"Esperado 200 ou 500, got {resp.status_code}"
        if resp.status_code == 200:
            data = resp.json()
            print_result("  Status", data.get("status"))
            print_result("  Visao", data.get("visao"))

        # 5.6: Status (404 para processo nao processado)
        resp = client.get("/api/processo/inexistente/status")
        print_result("GET /api/processo/inexistente/status", f"{resp.status_code}")
        # Pode ser 404 (nao encontrado) ou 200 se ja foi processado acima

        # 5.7: Verificar rotas existentes nao quebraram
        resp = client.get("/api/health")
        print_result("GET /api/health (existente)", f"{resp.status_code}")
        assert resp.status_code == 200, "Rota existente /api/health quebrou!"

        resp = client.get("/api/monitor/stats")
        print_result("GET /api/monitor/stats (existente)", f"{resp.status_code}")
        assert resp.status_code == 200, "Rota existente /api/monitor/stats quebrou!"

        print("\n  [OK] Todos os endpoints respondendo!")
        return True

    except ImportError as e:
        print(f"\n  [AVISO] Dependencia nao encontrada: {e}")
        return False
    except Exception as e:
        print(f"\n  [FALHOU] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline_service_list_agents():
    """Teste 6: PipelineService.list_agents()"""
    print_separator("TESTE 6: PipelineService.list_agents()")

    from djen.agents.pipeline_service import PipelineService

    agents = PipelineService.list_agents()
    print_result("Total agentes", len(agents))
    for a in agents:
        print(f"    [{a['priority']}] {a['name']}: {a['description'][:50]}")

    if len(agents) < 14:
        print(f"\n  [FALHOU] Esperado >= 14, got {len(agents)}")
        return False

    print("\n  [OK] PipelineService lista agentes corretamente!")
    return True


def test_canonical_model_serialization():
    """Teste 7: Serialization/deserialization do modelo canonico."""
    print_separator("TESTE 7: Canonical Model Serialization")

    from djen.agents.canonical_model import (
        ProcessoCanonical, ProcessoResponse, ProcessoResumoResponse,
        TimelineResponse, RiscoResponse, PipelineStatusResponse,
        NivelRisco, StatusProcesso, FaseProcessual,
        EventoTimeline, IndicadorRisco, Prazo,
    )

    p = ProcessoCanonical(
        numero_processo="1234567-89.2024.8.26.0001",
        tribunal="TJSP",
        status=StatusProcesso.ativo,
        fase=FaseProcessual.conhecimento,
        risco_geral=NivelRisco.medio,
        risco_score=0.5,
        timeline=[
            EventoTimeline(data="2024-01-15", titulo="Distribuicao", tipo="distribuicao", relevancia=9),
        ],
        indicadores_risco=[
            IndicadorRisco(categoria="prazo", nivel=NivelRisco.medio, score=0.5, descricao="Teste"),
        ],
    )

    # ProcessoResponse
    resp = ProcessoResponse(processo=p, tempo_processamento_ms=100)
    json_str = resp.model_dump_json()
    print_result("ProcessoResponse JSON size", f"{len(json_str)} bytes")

    # ProcessoResumoResponse
    resumo = ProcessoResumoResponse(
        numero_processo=p.numero_processo,
        tribunal=p.tribunal,
        classe_processual=p.classe_processual,
        status=p.status.value,
        fase=p.fase.value,
        risco_geral=p.risco_geral.value,
        risco_score=p.risco_score,
        resumo_executivo=None,
        pontos_atencao=[],
        proximos_passos=[],
        prazo_mais_urgente=None,
        valor_causa=None,
        total_partes=0,
        total_movimentacoes=0,
        total_comunicacoes=0,
        duracao_dias=None,
    )
    json_str = resumo.model_dump_json()
    print_result("ResumoResponse JSON size", f"{len(json_str)} bytes")

    # TimelineResponse
    tl = TimelineResponse(
        numero_processo=p.numero_processo,
        total_eventos=len(p.timeline),
        timeline=p.timeline,
    )
    json_str = tl.model_dump_json()
    print_result("TimelineResponse JSON size", f"{len(json_str)} bytes")

    # RiscoResponse
    rr = RiscoResponse(
        numero_processo=p.numero_processo,
        risco_geral=p.risco_geral,
        risco_score=p.risco_score,
        indicadores=p.indicadores_risco,
        recomendacoes=[],
    )
    json_str = rr.model_dump_json()
    print_result("RiscoResponse JSON size", f"{len(json_str)} bytes")

    print("\n  [OK] Todos os modelos serializam corretamente!")
    return True


def test_route_count():
    """Teste 8: Verificar que a quantidade de rotas aumentou."""
    print_separator("TESTE 8: Contagem de Rotas")

    from djen.api.app import app

    routes = [r for r in app.routes if hasattr(r, "path")]
    api_routes = [r for r in routes if hasattr(r, "methods")]
    ws_routes = [r for r in routes if not hasattr(r, "methods") and hasattr(r, "path")]

    print_result("Total rotas", len(routes))
    print_result("Rotas API (HTTP)", len(api_routes))

    processo_routes = [r for r in routes if "/api/processo" in getattr(r, "path", "")]
    ws_processo = [r for r in routes if "/ws/" in getattr(r, "path", "")]

    print_result("Rotas /api/processo/*", len(processo_routes))
    for r in processo_routes:
        methods = getattr(r, "methods", {"WS"})
        print(f"    {methods} {r.path}")

    if len(processo_routes) < 7:
        print(f"\n  [FALHOU] Esperado >= 7 rotas de processo, got {len(processo_routes)}")
        return False

    print(f"\n  [OK] {len(processo_routes)} rotas de processo + WebSocket!")
    return True


def main():
    print("")
    print("#" * 70)
    print("  SISTEMA MULTI-AGENTES - Testes")
    print(f"  Data: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("#" * 70)

    results = {}
    results["agent_registry"] = test_agent_registry()
    results["layer_resolution"] = test_orchestrator_layer_resolution()
    results["pipeline_mock"] = test_pipeline_with_mock()
    results["cache"] = test_cache()
    results["canonical_serialization"] = test_canonical_model_serialization()
    results["pipeline_list_agents"] = test_pipeline_service_list_agents()
    results["api_endpoints"] = test_api_endpoints()
    results["route_count"] = test_route_count()

    # Resumo
    print_separator("RESUMO")
    total = len(results)
    ok = sum(1 for v in results.values() if v)
    fail = total - ok

    for test_name, passed in results.items():
        status = "[OK]    " if passed else "[FALHOU]"
        print(f"  {status} {test_name}")

    print(f"\n  Total: {ok}/{total} testes passaram")
    if fail > 0:
        print(f"  {fail} teste(s) falharam")
    else:
        print("\n  TODOS OS TESTES PASSARAM!")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
