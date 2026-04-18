import requests, json, sys

session = requests.Session()
session.headers.update({
    "Authorization": "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
    "Content-Type": "application/json",
})

tribunais = ["stj", "stf", "tst", "tjsp", "tjrj", "tjmg", "tjrs", "tjpr", "trf1", "trf2", "trf3", "trf4", "trf5"]

print("=== TESTE DATAJUD - TODOS TRIBUNAIS ===\n")

for trib in tribunais:
    url = "https://api-publica.datajud.cnj.jus.br/api_publica_%s/_search" % trib
    query = {"size": 1, "query": {"match_all": {}}, "sort": [{"dataAjuizamento": {"order": "desc"}}]}
    try:
        resp = session.post(url, json=query, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("hits", {}).get("total", {}).get("value", 0)
            hits = data.get("hits", {}).get("hits", [])
            if hits:
                s = hits[0]["_source"]
                classe = s.get("classe", {}).get("nome", "?")
                proc = s.get("numeroProcesso", "?")
                grau = s.get("grau", "?")
                dt = s.get("dataAjuizamento", "?")[:10]
                print("[%6s] OK | %10d procs | %s | %s | %s | %s" % (trib.upper(), total, proc, classe, grau, dt))
            else:
                print("[%6s] OK | %10d procs | sem hits" % (trib.upper(), total))
        else:
            print("[%6s] HTTP %d" % (trib.upper(), resp.status_code))
    except requests.exceptions.Timeout:
        print("[%6s] TIMEOUT (25s)" % trib.upper())
    except Exception as e:
        print("[%6s] ERRO: %s" % (trib.upper(), str(e)[:80]))
    sys.stdout.flush()

print("\n=== TESTE BUSCA HABEAS CORPUS (classe cod 307) ===\n")

# Buscar Habeas Corpus pelo CODIGO da classe (307 = HC)
hc_tribunais = ["stj", "stf", "tjsp", "tjrj", "trf1", "trf3"]
for trib in hc_tribunais:
    url = "https://api-publica.datajud.cnj.jus.br/api_publica_%s/_search" % trib
    query = {
        "size": 3,
        "query": {"bool": {"must": [{"match": {"classe.codigo": 307}}]}},
        "sort": [{"dataAjuizamento": {"order": "desc"}}],
    }
    try:
        resp = session.post(url, json=query, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("hits", {}).get("total", {}).get("value", 0)
            hits = data.get("hits", {}).get("hits", [])
            print("[%6s] HC (cod 307): %d total" % (trib.upper(), total))
            for h in hits[:2]:
                s = h["_source"]
                proc = s.get("numeroProcesso", "?")
                dt = s.get("dataAjuizamento", "?")[:10]
                orgao = s.get("orgaoJulgador", {}).get("nome", "?")
                movs = s.get("movimentos", [])
                ult_mov = movs[-1].get("nome", "?") if movs else "sem mov"
                print("         %s | %s | %s | %s" % (proc, dt, orgao[:40], ult_mov[:40]))
        else:
            print("[%6s] HTTP %d" % (trib.upper(), resp.status_code))
    except requests.exceptions.Timeout:
        print("[%6s] TIMEOUT" % trib.upper())
    except Exception as e:
        print("[%6s] ERRO: %s" % (trib.upper(), str(e)[:80]))
    sys.stdout.flush()
