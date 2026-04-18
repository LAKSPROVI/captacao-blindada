#!/usr/bin/env python3
"""
Teste de conectividade e funcionalidade da API DJEN (CNJ).

API: https://comunicaapi.pje.jus.br/api/v1/comunicacao
Swagger: https://app.swaggerhub.com/apis-docs/cnj/pcp/1.0.0

IMPORTANTE: A API requer IP brasileiro. Este script usa proxy residencial BR
automaticamente via Bright Data.

Uso:
    python -m djen.scripts.test_djen_api
    python djen/scripts/test_djen_api.py
"""

import json
import sys
import os
import time
from datetime import datetime, timedelta

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# === CONFIG ===
API_BASE = "https://comunicaapi.pje.jus.br"
API_PATH = "/api/v1/comunicacao"
API_URL = f"{API_BASE}{API_PATH}"

# Proxy residencial BR (Bright Data) - necessario para IP brasileiro
PROXY_URL = (
    "http://brd-customer-hl_9fcf364a-zone-residential_proxy1-country-br"
    ":a42i721ykgk9@brd.superproxy.io:33335"
)
PROXIES = {"http": PROXY_URL, "https": PROXY_URL}

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Datas para testes
DATA_FIM = datetime.now().strftime("%Y-%m-%d")
DATA_INICIO = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")


def print_separator(title):
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)


def print_result(label, value):
    print(f"  {label}: {value}")


def test_health_check():
    """Teste 1: Verificar se a API esta acessivel."""
    print_separator("TESTE 1: Health Check (API acessivel?)")

    params = {
        "pagina": 0,
        "itensPorPagina": 1,
        "siglaTribunal": "TJMA",
        "dataDisponibilizacaoInicio": DATA_INICIO,
        "dataDisponibilizacaoFim": DATA_FIM,
    }

    try:
        t0 = time.time()
        resp = requests.get(API_URL, params=params, headers=HEADERS,
                           proxies=PROXIES, timeout=30, verify=False)
        elapsed = time.time() - t0

        print_result("Status HTTP", resp.status_code)
        print_result("Tempo resposta", f"{elapsed:.2f}s")

        if resp.status_code == 200:
            data = resp.json()
            print_result("Status API", data.get("status", "N/A"))
            print_result("Count", data.get("count", 0))
            print_result("Items retornados", len(data.get("items", [])))
            print("\n  [OK] API DJEN acessivel via proxy BR!")
            return True
        elif resp.status_code == 403:
            print("\n  [ERRO] HTTP 403 - IP nao brasileiro. Verifique o proxy.")
            return False
        else:
            print(f"\n  [ERRO] HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"\n  [ERRO] {e}")
        return False


def test_busca_por_processo():
    """Teste 2: Buscar comunicacoes por numero de processo."""
    print_separator("TESTE 2: Busca por Numero de Processo")

    params = {
        "numeroProcesso": "0044631-56.2012.8.10.0001",
        "pagina": 0,
        "itensPorPagina": 5,
    }

    try:
        t0 = time.time()
        resp = requests.get(API_URL, params=params, headers=HEADERS,
                           proxies=PROXIES, timeout=30, verify=False)
        elapsed = time.time() - t0

        print_result("Processo", params["numeroProcesso"])
        print_result("Status HTTP", resp.status_code)
        print_result("Tempo", f"{elapsed:.2f}s")

        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", 0)
            items = data.get("items", [])
            print_result("Total comunicacoes", count)
            print_result("Items retornados", len(items))

            if items:
                item = items[0]
                print("\n  --- Primeira comunicacao ---")
                print_result("  ID", item.get("id"))
                print_result("  Tribunal", item.get("siglaTribunal"))
                print_result("  Orgao", item.get("nomeOrgao"))
                print_result("  Tipo", item.get("tipoComunicacao"))
                print_result("  Classe", item.get("nomeClasse"))
                print_result("  Data", item.get("data_disponibilizacao"))
                print_result("  Meio", item.get("meiocompleto"))

                # Destinatarios
                dests = item.get("destinatarios", [])
                if dests:
                    print_result("  Partes", "; ".join(d.get("nome", "") for d in dests))

                # Advogados
                advs = item.get("destinatarioadvogados", [])
                if advs:
                    adv_strs = []
                    for a in advs:
                        adv = a.get("advogado", {})
                        nome = adv.get("nome", "")
                        oab = adv.get("numero_oab", "")
                        uf = adv.get("uf_oab", "")
                        adv_strs.append(f"{nome} (OAB {oab}/{uf})")
                    print_result("  Advogados", "; ".join(adv_strs))

                # Texto (primeiros 200 chars)
                texto = item.get("texto", "")
                if texto:
                    print_result("  Texto (trecho)", texto[:200] + "...")

            return count > 0
        else:
            print(f"\n  [ERRO] HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"\n  [ERRO] {e}")
        return False


def test_busca_por_oab():
    """Teste 3: Buscar comunicacoes por numero de OAB."""
    print_separator("TESTE 3: Busca por OAB")

    params = {
        "numeroOab": "123456",
        "ufOab": "SP",
        "pagina": 0,
        "itensPorPagina": 3,
        "dataDisponibilizacaoInicio": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        "dataDisponibilizacaoFim": DATA_FIM,
    }

    try:
        t0 = time.time()
        resp = requests.get(API_URL, params=params, headers=HEADERS,
                           proxies=PROXIES, timeout=30, verify=False)
        elapsed = time.time() - t0

        print_result("OAB", f"{params['numeroOab']}/{params['ufOab']}")
        print_result("Status HTTP", resp.status_code)
        print_result("Tempo", f"{elapsed:.2f}s")

        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", 0)
            items = data.get("items", [])
            print_result("Total comunicacoes", count)
            print_result("Items retornados", len(items))

            if items:
                for i, item in enumerate(items[:3]):
                    print(f"\n  --- Comunicacao {i+1} ---")
                    print_result("  Tribunal", item.get("siglaTribunal"))
                    proc = item.get("numeroprocessocommascara", item.get("numero_processo"))
                    print_result("  Processo", proc)
                    print_result("  Tipo", item.get("tipoComunicacao"))
                    print_result("  Data", item.get("data_disponibilizacao"))

            return True
        else:
            print(f"\n  [ERRO] HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"\n  [ERRO] {e}")
        return False


def test_busca_por_tribunal():
    """Teste 4: Buscar comunicacoes por tribunal e data."""
    print_separator("TESTE 4: Busca por Tribunal + Data")

    params = {
        "siglaTribunal": "TRF4",
        "dataDisponibilizacaoInicio": DATA_INICIO,
        "dataDisponibilizacaoFim": DATA_FIM,
        "pagina": 0,
        "itensPorPagina": 3,
    }

    try:
        t0 = time.time()
        resp = requests.get(API_URL, params=params, headers=HEADERS,
                           proxies=PROXIES, timeout=30, verify=False)
        elapsed = time.time() - t0

        print_result("Tribunal", params["siglaTribunal"])
        periodo = f"{params['dataDisponibilizacaoInicio']} a {params['dataDisponibilizacaoFim']}"
        print_result("Periodo", periodo)
        print_result("Status HTTP", resp.status_code)
        print_result("Tempo", f"{elapsed:.2f}s")

        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", 0)
            items = data.get("items", [])
            print_result("Total comunicacoes", count)
            print_result("Items retornados", len(items))

            if items:
                item = items[0]
                print("\n  --- Exemplo ---")
                print_result("  Processo", item.get("numeroprocessocommascara"))
                print_result("  Orgao", item.get("nomeOrgao"))
                print_result("  Tipo", item.get("tipoComunicacao"))

            return count > 0
        else:
            print(f"\n  [ERRO] HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"\n  [ERRO] {e}")
        return False


def test_djen_source_class():
    """Teste 5: Testar a classe DjenSource integrada."""
    print_separator("TESTE 5: Classe DjenSource (integracao)")

    try:
        from djen.sources.djen_source import DjenSource

        source = DjenSource()
        print_result("Classe", "DjenSource instanciada com sucesso")

        # Health check
        health = source.health_check()
        print_result("Health status", health.get("status"))
        print_result("Health message", health.get("message"))
        print_result("Proxy usado", health.get("proxy_used"))

        if health["status"] == "ok":
            # Busca por processo
            resultados = source.buscar_por_processo("0044631-56.2012.8.10.0001")
            print_result("Resultados busca processo", len(resultados))

            if resultados:
                r = resultados[0]
                print_result("  Fonte", r.fonte)
                print_result("  Tribunal", r.tribunal)
                print_result("  Processo", r.numero_processo)
                print_result("  Data", r.data_publicacao)
                print_result("  Advogados", r.advogados[:3])
                print_result("  OABs", r.oab_encontradas[:3])

            # Listar tribunais
            tribunais = source.listar_tribunais()
            print_result("Tribunais disponiveis", len(tribunais))

            print("\n  [OK] DjenSource funcionando!")
            return True
        else:
            print("\n  [ERRO] Health check falhou")
            return False

    except ImportError as e:
        print(f"\n  [AVISO] Nao foi possivel importar DjenSource: {e}")
        print("  Execute de dentro do diretorio do projeto.")
        return False
    except Exception as e:
        print(f"\n  [ERRO] {e}")
        return False


def main():
    print("")
    print("#" * 70)
    print("  DJEN API - Teste de Conectividade e Funcionalidade")
    print(f"  API: {API_URL}")
    print("  Swagger: https://app.swaggerhub.com/apis-docs/cnj/pcp/1.0.0")
    print("  Proxy: Bright Data Residential (IP BR)")
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("#" * 70)

    results = {}
    results["health_check"] = test_health_check()
    results["busca_processo"] = test_busca_por_processo()
    results["busca_oab"] = test_busca_por_oab()
    results["busca_tribunal"] = test_busca_por_tribunal()
    results["djen_source"] = test_djen_source_class()

    # Resumo
    print_separator("RESUMO")
    total = len(results)
    ok = sum(1 for v in results.values() if v)
    fail = total - ok

    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FALHOU]"
        print(f"  {status} {test_name}")

    print(f"\n  Total: {ok}/{total} testes passaram")
    if fail > 0:
        print(f"  {fail} teste(s) falharam")
    else:
        print("\n  TODOS OS TESTES PASSARAM!")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
