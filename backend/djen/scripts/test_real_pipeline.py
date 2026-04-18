#!/usr/bin/env python3
"""
Teste real do pipeline multi-agentes com processo conhecido.

Usa o processo 0044631-56.2012.8.10.0001 (TJMA) que ja retornou
dados no DJEN anteriormente.

IMPORTANTE: Requer proxy BR para DJEN (ja configurado em DjenSource).
DataJud pode ou nao retornar dados dependendo do tribunal.

Uso:
    python -m djen.scripts.test_real_pipeline
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    print("#" * 70)
    print("  TESTE REAL - Pipeline Multi-Agentes")
    print(f"  Data: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("#" * 70)

    from djen.agents.pipeline_service import PipelineService

    service = PipelineService()
    numero = "0044631-56.2012.8.10.0001"

    print(f"\n  Processo: {numero}")
    print("  Executando pipeline completo (pode levar 10-30s)...\n")

    t0 = time.time()
    try:
        processo = service.analisar(numero, force_refresh=True)
    except Exception as e:
        print(f"\n  [ERRO] Pipeline falhou: {e}")
        import traceback
        traceback.print_exc()
        return 1

    elapsed = time.time() - t0

    print("=" * 70)
    print("  RESULTADO")
    print("=" * 70)

    def pr(label, value):
        print(f"  {label}: {value}")

    pr("Numero", processo.numero_formatado or processo.numero_processo)
    pr("Tribunal", processo.tribunal)
    pr("Classe", processo.classe_processual)
    pr("Orgao Julgador", processo.orgao_julgador)
    pr("Area", processo.area)
    pr("Fase", processo.fase.value if processo.fase else "N/A")
    pr("Status", processo.status.value if processo.status else "N/A")
    pr("Justica", processo.justica)
    pr("Grau", processo.grau)
    pr("Data Ajuizamento", processo.data_ajuizamento)
    pr("Data Ult. Movimentacao", processo.data_ultima_movimentacao)
    pr("Duracao (dias)", processo.duracao_dias)
    pr("Formato", processo.formato_origem)
    pr("Sistema", processo.sistema_origem)
    pr("Sigilo", processo.nivel_sigilo)

    print("\n--- Partes ---")
    pr("Total", processo.total_partes)
    for p in processo.partes[:10]:
        pr(f"  {p.polo.value}", f"{p.nome} ({p.tipo.value})")

    print("\n--- Advogados ---")
    pr("Total", len(processo.advogados))
    for a in processo.advogados[:10]:
        pr(f"  OAB {a.oab}/{a.uf_oab}", a.nome)

    print("\n--- Movimentacoes ---")
    pr("Total", processo.total_movimentacoes)
    if processo.movimentacoes:
        for m in processo.movimentacoes[:5]:
            pr(f"  [{m.tipo or '?'}]", f"{m.data[:10]} - {m.nome}")

    print("\n--- Comunicacoes (DJEN) ---")
    pr("Total", processo.total_comunicacoes)
    for c in processo.comunicacoes[:3]:
        pr(f"  {c.tipo}", f"{c.data_disponibilizacao} - {c.orgao}")

    print("\n--- Valores ---")
    pr("Valor da causa", f"R$ {processo.valor_causa:,.2f}" if processo.valor_causa else "N/A")
    for v in processo.valores[:5]:
        pr(f"  {v.tipo}", f"R$ {v.valor:,.2f}")

    print("\n--- Prazos ---")
    pr("Total", len(processo.prazos))
    for p in processo.prazos[:3]:
        status = "VENCIDO" if (p.dias_restantes or 0) < 0 else f"{p.dias_restantes} dias"
        pr(f"  {p.tipo}", f"{p.data_fim} ({status})")

    print("\n--- Risco ---")
    pr("Risco Geral", f"{processo.risco_geral.value} (score={processo.risco_score})")
    for ind in processo.indicadores_risco:
        pr(f"  [{ind.categoria}]", f"{ind.nivel.value} - {ind.descricao[:70]}")

    print("\n--- Timeline ---")
    pr("Total eventos", len(processo.timeline))
    for e in processo.timeline[:5]:
        pr(f"  [{e.tipo}]", f"{e.data[:10]} - {e.titulo[:60]}")

    print("\n--- Resumo Executivo ---")
    print(f"  {processo.resumo_executivo}")

    print("\n--- Situacao Atual ---")
    print(f"  {processo.resumo_situacao_atual}")

    print("\n--- Pontos de Atencao ---")
    for pa in processo.pontos_atencao:
        print(f"  - {pa[:80]}")

    print("\n--- Proximos Passos ---")
    for pp in processo.proximos_passos:
        print(f"  - {pp[:80]}")

    print("\n--- Agentes Executados ---")
    for ar in processo.agents_executed:
        status = ar.status.value
        dur = f"{ar.duration_ms}ms" if ar.duration_ms else "N/A"
        err = f" ERRO: {ar.error}" if ar.error else ""
        print(f"  [{status:>9}] {ar.agent_name} ({dur}){err}")

    print("\n--- Meta ---")
    pr("Fontes consultadas", processo.fontes_consultadas)
    pr("Tempo processamento", f"{processo.processing_time_ms}ms")
    pr("Enriched at", processo.enriched_at)
    pr("Tempo total (wall)", f"{elapsed:.1f}s")

    # Verificar resultados
    completed = sum(1 for ar in processo.agents_executed if ar.status.value == "completed")
    failed = sum(1 for ar in processo.agents_executed if ar.status.value == "failed")

    print("\n" + "=" * 70)
    print(f"  CONCLUSAO: {completed} agentes OK, {failed} falharam")
    if processo.fontes_consultadas:
        print(f"  Fontes: {', '.join(processo.fontes_consultadas)}")
    print("=" * 70)

    # Testar via API tambem
    print("\n\n--- Teste via API TestClient ---")
    try:
        from fastapi.testclient import TestClient
        from djen.api.app import app

        client = TestClient(app, raise_server_exceptions=False)

        # GET /api/processo/{numero} (deve usar cache)
        t1 = time.time()
        resp = client.get(f"/api/processo/{numero}")
        t2 = time.time()
        pr("GET /api/processo/{numero}", f"{resp.status_code} ({(t2-t1)*1000:.0f}ms)")
        if resp.status_code == 200:
            data = resp.json()
            pr("  Visao", data.get("visao"))
            pr("  Tempo proc", f"{data.get('tempo_processamento_ms')}ms")

        # Resumo
        resp = client.get(f"/api/processo/{numero}/resumo")
        pr("GET .../resumo", f"{resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            pr("  Risco", data.get("risco_geral"))
            pr("  Status", data.get("status"))

        # Timeline
        resp = client.get(f"/api/processo/{numero}/timeline?min_relevancia=5")
        pr("GET .../timeline", f"{resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            pr("  Eventos (rel>=5)", data.get("total_eventos"))

        # Riscos
        resp = client.get(f"/api/processo/{numero}/riscos")
        pr("GET .../riscos", f"{resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            pr("  Indicadores", len(data.get("indicadores", [])))
            pr("  Recomendacoes", len(data.get("recomendacoes", [])))

        # Status
        resp = client.get(f"/api/processo/{numero}/status")
        pr("GET .../status", f"{resp.status_code}")

        print("\n  [OK] Todos os endpoints responderam com sucesso!")

    except Exception as e:
        print(f"\n  [AVISO] Teste API falhou: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
