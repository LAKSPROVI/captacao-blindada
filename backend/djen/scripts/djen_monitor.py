#!/usr/bin/env python3
"""
DJEN Monitor v2.0 - Sistema de Monitoramento de Publicacoes Judiciais

Fontes reais validadas:
- DataJud API (CNJ) - Elasticsearch, cobre todos tribunais
- DJe TJSP - Busca avancada por texto
- DEJT - Justica do Trabalho
- Querido Diario API - Diarios oficiais municipais

Uso:
    python3 djen_monitor.py --help
    python3 djen_monitor.py add advogado "NOME" --nome "Dr. Fulano"
    python3 djen_monitor.py buscar --termo "HABEAS CORPUS" --fonte datajud --tribunal stj
    python3 djen_monitor.py monitor --dias 1
    python3 djen_monitor.py health
"""

import os
import sys
import json
import sqlite3
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Adicionar diretorio pai ao path para imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from djen.sources.datajud import DatajudSource
from djen.sources.tjsp_dje import TJSPDjeSource
from djen.sources.dejt import DEJTSource
from djen.sources.querido_diario import QueridoDiarioSource
from djen.sources.jusbrasil import JusBrasilSource
from djen.sources.base import PublicacaoResult
from djen.legal_parser import LegalParser
from djen.notifier import Notifier, NotificationConfig

# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent / "djen"

# Verificar se estamos no servidor ou local
if Path("/opt/CAPTAÇÃO BLINDADA/djen").exists():
    BASE_DIR = Path("/opt/CAPTAÇÃO BLINDADA/djen")

DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
DB_PATH = DATA_DIR / "publicacoes.db"
LOG_PATH = DATA_DIR / "djen_monitor.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("djen")

# ============================================================
# FONTES DISPONIVEIS
# ============================================================

SOURCES = {
    "datajud": DatajudSource,
    "tjsp": TJSPDjeSource,
    "dejt": DEJTSource,
    "querido_diario": QueridoDiarioSource,
    "jusbrasil": JusBrasilSource,
}

# Mapeamento fonte -> instancia (lazy)
_source_instances = {}

def get_source(nome: str):
    """Obtem instancia da fonte (singleton)."""
    if nome not in _source_instances:
        if nome not in SOURCES:
            raise ValueError(f"Fonte '{nome}' nao disponivel. Opcoes: {', '.join(SOURCES.keys())}")
        # JusBrasil precisa de credenciais do config
        if nome == "jusbrasil":
            creds_path = CONFIG_DIR / "credentials.json"
            config = {}
            if creds_path.exists():
                import json as _json
                try:
                    config = _json.loads(creds_path.read_text()).get("jusbrasil", {})
                except Exception:
                    pass
            _source_instances[nome] = SOURCES[nome](config=config)
        else:
            _source_instances[nome] = SOURCES[nome]()
    return _source_instances[nome]

# ============================================================
# BANCO DE DADOS
# ============================================================

def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitorados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            valor TEXT NOT NULL,
            nome_amigavel TEXT,
            ativo INTEGER DEFAULT 1,
            fontes TEXT DEFAULT 'datajud,tjsp',
            tribunal TEXT,
            criado_em TEXT DEFAULT (datetime('now')),
            UNIQUE(tipo, valor)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS publicacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE NOT NULL,
            fonte TEXT NOT NULL,
            tribunal TEXT,
            data_publicacao TEXT NOT NULL,
            caderno TEXT,
            pagina TEXT,
            conteudo TEXT NOT NULL,
            numero_processo TEXT,
            classe_processual TEXT,
            orgao_julgador TEXT,
            assuntos TEXT,
            oab_encontradas TEXT,
            advogados TEXT,
            partes TEXT,
            termos_encontrados TEXT,
            monitorado_id INTEGER,
            url_origem TEXT,
            notificado INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (monitorado_id) REFERENCES monitorados(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS buscas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            fonte TEXT,
            tribunal TEXT,
            data_busca TEXT,
            termos TEXT,
            resultados INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ok',
            erro TEXT,
            duracao_ms INTEGER,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    # Indices
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pub_data ON publicacoes(data_publicacao)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pub_fonte ON publicacoes(fonte)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pub_notif ON publicacoes(notificado)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pub_hash ON publicacoes(hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pub_processo ON publicacoes(numero_processo)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pub_tribunal ON publicacoes(tribunal)")
    conn.commit()
    return conn

# ============================================================
# GERENCIAMENTO DE MONITORADOS
# ============================================================

def adicionar_monitorado(conn, tipo, valor, nome_amigavel=None, fontes=None, tribunal=None):
    try:
        conn.execute(
            "INSERT OR IGNORE INTO monitorados (tipo, valor, nome_amigavel, fontes, tribunal) VALUES (?, ?, ?, ?, ?)",
            (tipo, valor.upper().strip(), nome_amigavel or valor,
             ",".join(fontes) if fontes else "datajud,tjsp",
             tribunal)
        )
        conn.commit()
        log.info("Monitorado adicionado: [%s] %s (%s)", tipo, valor, nome_amigavel)
        return True
    except Exception as e:
        log.error("Erro ao adicionar monitorado: %s", e)
        return False

def listar_monitorados(conn, apenas_ativos=True):
    query = "SELECT id, tipo, valor, nome_amigavel, ativo, fontes, tribunal, criado_em FROM monitorados"
    if apenas_ativos:
        query += " WHERE ativo = 1"
    return conn.execute(query).fetchall()

def remover_monitorado(conn, monitorado_id):
    conn.execute("UPDATE monitorados SET ativo = 0 WHERE id = ?", (monitorado_id,))
    conn.commit()

# ============================================================
# MOTOR DE BUSCA PRINCIPAL
# ============================================================

def executar_busca(
    conn,
    termos: Optional[List[str]] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    fontes: Optional[List[str]] = None,
    tribunal: Optional[str] = None,
    notificar: bool = True,
) -> int:
    """Executa busca em todas as fontes configuradas."""
    parser = LegalParser()
    
    if not data_inicio:
        data_inicio = datetime.now().strftime("%d/%m/%Y")
    if not data_fim:
        data_fim = data_inicio

    # Determinar termos
    if termos:
        termos_lista = [(None, "manual", t, t, fontes or ["datajud", "tjsp"], tribunal) for t in termos]
    else:
        monitorados = listar_monitorados(conn)
        termos_lista = []
        for m in monitorados:
            # m: (id, tipo, valor, nome_amigavel, ativo, fontes, tribunal, criado_em)
            m_fontes = (m[5] or "datajud,tjsp").split(",")
            m_tribunal = m[6]
            termos_lista.append((m[0], m[1], m[2], m[3], m_fontes, m_tribunal))

    if not fontes:
        fontes = ["datajud", "tjsp"]

    total_novos = 0
    publicacoes_novas = []

    for mon_id, tipo, valor, nome, item_fontes, item_tribunal in termos_lista:
        log.info("--- Buscando: [%s] %s (%s) ---", tipo, valor, nome)

        # Usar fontes do item ou as especificadas
        fontes_busca = fontes if termos else item_fontes
        tribunal_busca = tribunal or item_tribunal

        resultados = []
        import time

        for fonte_nome in fontes_busca:
            fonte_nome = fonte_nome.strip()
            if fonte_nome not in SOURCES:
                log.warning("Fonte '%s' nao disponivel, pulando", fonte_nome)
                continue

            t0 = time.time()
            try:
                source = get_source(fonte_nome)
                results = source.buscar(
                    termo=valor,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    tribunal=tribunal_busca,
                )
                resultados.extend(results)
                duracao = int((time.time() - t0) * 1000)

                # Registrar busca
                conn.execute("""
                    INSERT INTO buscas (tipo, fonte, tribunal, data_busca, termos, resultados, status, duracao_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "automatica" if not termos else "manual",
                    fonte_nome, tribunal_busca, data_inicio, valor,
                    len(results), "ok", duracao
                ))

            except Exception as e:
                duracao = int((time.time() - t0) * 1000)
                log.error("[%s] Erro: %s", fonte_nome, e)
                conn.execute("""
                    INSERT INTO buscas (tipo, fonte, tribunal, data_busca, termos, resultados, status, erro, duracao_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "automatica" if not termos else "manual",
                    fonte_nome, tribunal_busca, data_inicio, valor,
                    0, "erro", str(e), duracao
                ))

        # Salvar resultados no banco
        novos = 0
        for r in resultados:
            # Enriquecer com parser juridico
            dados_juridicos = parser.extrair_tudo(r.conteudo)

            # Mesclar OABs e advogados encontrados pelo parser
            oabs = r.oab_encontradas or []
            oabs.extend([f"{o['numero']}/{o['uf']}" for o in dados_juridicos.get("oabs", [])])
            advogados = r.advogados or []
            advogados.extend(dados_juridicos.get("advogados", []))
            processos = dados_juridicos.get("processos", [])
            if r.numero_processo and r.numero_processo not in processos:
                processos.insert(0, r.numero_processo)

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO publicacoes
                    (hash, fonte, tribunal, data_publicacao, caderno, pagina,
                     conteudo, numero_processo, classe_processual, orgao_julgador,
                     assuntos, oab_encontradas, advogados, partes,
                     termos_encontrados, monitorado_id, url_origem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.hash, r.fonte, r.tribunal, r.data_publicacao,
                    r.caderno, r.pagina, r.conteudo[:10000],
                    processos[0] if processos else r.numero_processo,
                    r.classe_processual,
                    r.orgao_julgador,
                    json.dumps(r.assuntos or dados_juridicos.get("classes", []), ensure_ascii=False),
                    json.dumps(list(set(oabs)), ensure_ascii=False),
                    json.dumps(list(set(advogados)), ensure_ascii=False),
                    json.dumps(dados_juridicos.get("nomes_caps", []), ensure_ascii=False),
                    json.dumps([valor], ensure_ascii=False),
                    mon_id,
                    r.url_origem,
                ))
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    novos += 1
                    pub_dict = r.to_dict()
                    pub_dict["monitorado_nome"] = nome
                    publicacoes_novas.append(pub_dict)
            except Exception as e:
                log.error("Erro ao salvar publicacao: %s", e)

        conn.commit()
        total_novos += novos
        log.info("    %d publicacoes novas salvas (de %d encontradas)", novos, len(resultados))

    # Notificar
    if notificar and publicacoes_novas:
        try:
            notif_config = NotificationConfig(
                config_path=CONFIG_DIR / "notifications.json"
            )
            notifier = notif_config.get_notifier()
            notifier.notificar_publicacoes(publicacoes_novas, conn)
        except Exception as e:
            log.error("Erro ao notificar: %s", e)

    return total_novos

# ============================================================
# RELATORIOS
# ============================================================

def relatorio_publicacoes(conn, data=None, nao_notificadas=False, fonte=None,
                          tribunal=None, limite=50):
    query = """SELECT p.id, p.fonte, p.tribunal, p.data_publicacao, p.conteudo,
               p.numero_processo, p.classe_processual, p.orgao_julgador,
               p.oab_encontradas, p.advogados,
               p.termos_encontrados, p.url_origem, p.criado_em, m.nome_amigavel
               FROM publicacoes p
               LEFT JOIN monitorados m ON p.monitorado_id = m.id
               WHERE 1=1"""
    params = []
    if data:
        query += " AND p.data_publicacao = ?"
        params.append(data)
    if nao_notificadas:
        query += " AND p.notificado = 0"
    if fonte:
        query += " AND p.fonte = ?"
        params.append(fonte)
    if tribunal:
        query += " AND p.tribunal = ?"
        params.append(tribunal.upper())
    query += " ORDER BY p.criado_em DESC LIMIT ?"
    params.append(limite)
    return conn.execute(query, params).fetchall()

def formatar_relatorio(publicacoes):
    if not publicacoes:
        return "Nenhuma publicacao encontrada."
    linhas = []
    linhas.append("\n=== RELATORIO DE PUBLICACOES ({} resultados) ===\n".format(len(publicacoes)))
    for p in publicacoes:
        (pid, fonte, tribunal, data, conteudo, processo, classe, orgao,
         oabs, advogados, termos, url, criado, monitorado) = p
        linhas.append("--- Publicacao #{} ---".format(pid))
        linhas.append("Fonte: {} | Tribunal: {}".format(fonte.upper(), tribunal or "N/A"))
        linhas.append("Data: {}".format(data))
        if processo:
            linhas.append("Processo: {}".format(processo))
        if classe:
            linhas.append("Classe: {}".format(classe))
        if orgao:
            linhas.append("Orgao: {}".format(orgao))
        if monitorado:
            linhas.append("Monitorado: {}".format(monitorado))
        if oabs:
            linhas.append("OABs: {}".format(oabs))
        if advogados:
            linhas.append("Advogados: {}".format(advogados))
        linhas.append("Conteudo:\n{}...".format(conteudo[:600]))
        if url:
            linhas.append("URL: {}".format(url))
        linhas.append("")
    return "\n".join(linhas)

# ============================================================
# ESTATISTICAS
# ============================================================

def estatisticas(conn):
    stats = {}
    stats["total_publicacoes"] = conn.execute("SELECT COUNT(*) FROM publicacoes").fetchone()[0]
    stats["nao_notificadas"] = conn.execute("SELECT COUNT(*) FROM publicacoes WHERE notificado = 0").fetchone()[0]
    stats["monitorados_ativos"] = conn.execute("SELECT COUNT(*) FROM monitorados WHERE ativo = 1").fetchone()[0]
    stats["total_buscas"] = conn.execute("SELECT COUNT(*) FROM buscas").fetchone()[0]
    stats["por_fonte"] = dict(conn.execute("SELECT fonte, COUNT(*) FROM publicacoes GROUP BY fonte").fetchall())
    stats["por_tribunal"] = dict(conn.execute(
        "SELECT tribunal, COUNT(*) FROM publicacoes WHERE tribunal IS NOT NULL GROUP BY tribunal"
    ).fetchall())
    stats["ultimas_buscas"] = conn.execute(
        "SELECT fonte, tribunal, data_busca, resultados, status, duracao_ms, criado_em "
        "FROM buscas ORDER BY criado_em DESC LIMIT 10"
    ).fetchall()
    return stats

# ============================================================
# HEALTH CHECK
# ============================================================

def health_check_all():
    """Verifica conectividade com todas as fontes."""
    results = []
    for nome, cls in SOURCES.items():
        try:
            source = get_source(nome)
            result = source.health_check()
            results.append(result)
        except Exception as e:
            results.append({
                "source": nome,
                "status": "error",
                "message": str(e),
            })
    return results

# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="DJEN Monitor v2.0 - Monitoramento de Publicacoes Judiciais",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Fontes disponiveis:
  datajud        DataJud API (CNJ) - Todos tribunais, busca por processo
  tjsp           DJe TJSP - Busca textual (nome, OAB, processo)
  dejt           DEJT - Justica do Trabalho
  querido_diario Querido Diario API - Diarios oficiais municipais

Exemplos:
  %(prog)s add advogado "JOAO SILVA" --nome "Dr. Joao" --fontes datajud tjsp
  %(prog)s add oab "123456/SP" --nome "Dr. Joao"
  %(prog)s add processo "1234567-89.2024.8.26.0100" --tribunal tjsp
  %(prog)s buscar --termo "HABEAS CORPUS" --fonte datajud --tribunal stj
  %(prog)s buscar --termo "123456/SP" --fonte tjsp
  %(prog)s monitor --dias 1
  %(prog)s health
  %(prog)s stats
"""
    )
    sub = parser.add_subparsers(dest="comando")

    # Adicionar monitorado
    add_p = sub.add_parser("add", help="Adicionar advogado/OAB/processo para monitorar")
    add_p.add_argument("tipo", choices=["advogado", "oab", "processo", "parte"])
    add_p.add_argument("valor", help="Nome, numero OAB, numero processo, etc")
    add_p.add_argument("--nome", help="Nome amigavel para identificacao")
    add_p.add_argument("--fontes", nargs="+", choices=list(SOURCES.keys()),
                       default=["datajud", "tjsp"], help="Fontes para buscar")
    add_p.add_argument("--tribunal", help="Tribunal especifico (ex: stj, tjsp)")

    # Listar monitorados
    sub.add_parser("list", help="Listar todos os monitorados")

    # Remover
    rm_p = sub.add_parser("remove", help="Desativar um monitorado")
    rm_p.add_argument("id", type=int)

    # Buscar
    busca_p = sub.add_parser("buscar", help="Executar busca manual")
    busca_p.add_argument("--termo", nargs="+", help="Termos para buscar")
    busca_p.add_argument("--data-inicio", help="Data inicio (DD/MM/AAAA)")
    busca_p.add_argument("--data-fim", help="Data fim (DD/MM/AAAA)")
    busca_p.add_argument("--fonte", nargs="+", choices=list(SOURCES.keys()),
                         help="Fontes (default: datajud,tjsp)")
    busca_p.add_argument("--tribunal", help="Tribunal especifico")
    busca_p.add_argument("--sem-notificacao", action="store_true", help="Nao enviar notificacoes")

    # Relatorio
    rel_p = sub.add_parser("relatorio", help="Ver publicacoes encontradas")
    rel_p.add_argument("--data", help="Filtrar por data (DD/MM/AAAA)")
    rel_p.add_argument("--novas", action="store_true", help="Apenas nao notificadas")
    rel_p.add_argument("--fonte", help="Filtrar por fonte")
    rel_p.add_argument("--tribunal", help="Filtrar por tribunal")
    rel_p.add_argument("--limite", type=int, default=50)

    # Stats
    sub.add_parser("stats", help="Estatisticas do sistema")

    # Health check
    sub.add_parser("health", help="Verificar conectividade com as fontes")

    # Monitor (cron)
    mon_p = sub.add_parser("monitor", help="Executar monitoramento automatico (para cron)")
    mon_p.add_argument("--dias", type=int, default=1, help="Quantos dias para tras buscar")

    # Fontes
    sub.add_parser("fontes", help="Listar fontes disponiveis e tribunais")

    # Parse
    parse_p = sub.add_parser("parse", help="Testar parser juridico em um texto")
    parse_p.add_argument("texto", help="Texto para analisar")

    # Notificacao
    notif_p = sub.add_parser("notif", help="Gerenciar notificacoes")
    notif_sub = notif_p.add_subparsers(dest="notif_cmd")
    notif_add_wa = notif_sub.add_parser("add-whatsapp", help="Adicionar numero WhatsApp")
    notif_add_wa.add_argument("numero", help="Numero (ex: 5511999999999)")
    notif_add_email = notif_sub.add_parser("add-email", help="Adicionar email")
    notif_add_email.add_argument("email")
    notif_sub.add_parser("show", help="Mostrar configuracao de notificacoes")

    args = parser.parse_args()
    conn = init_db()

    if args.comando == "add":
        adicionar_monitorado(conn, args.tipo, args.valor, args.nome,
                             fontes=args.fontes, tribunal=args.tribunal)
        print("Adicionado: [{}] {} (fontes: {})".format(args.tipo, args.valor, ",".join(args.fontes)))

    elif args.comando == "list":
        monitorados = listar_monitorados(conn)
        if not monitorados:
            print("Nenhum monitorado cadastrado.")
        else:
            print("{:<5} {:<12} {:<35} {:<25} {:<20} {}".format(
                "ID", "Tipo", "Valor", "Nome", "Fontes", "Tribunal"))
            print("-" * 110)
            for m in monitorados:
                print("{:<5} {:<12} {:<35} {:<25} {:<20} {}".format(
                    m[0], m[1], m[2][:35], (m[3] or "")[:25],
                    (m[5] or "datajud,tjsp")[:20], m[6] or "todos"))

    elif args.comando == "remove":
        remover_monitorado(conn, args.id)
        print("Monitorado #{} desativado.".format(args.id))

    elif args.comando == "buscar":
        novos = executar_busca(
            conn,
            termos=args.termo,
            data_inicio=args.data_inicio,
            data_fim=args.data_fim,
            fontes=args.fonte,
            tribunal=args.tribunal,
            notificar=not args.sem_notificacao,
        )
        print("\nBusca concluida: {} novas publicacoes encontradas.".format(novos))

    elif args.comando == "relatorio":
        pubs = relatorio_publicacoes(
            conn, data=args.data, nao_notificadas=args.novas,
            fonte=args.fonte, tribunal=args.tribunal, limite=args.limite
        )
        print(formatar_relatorio(pubs))

    elif args.comando == "stats":
        s = estatisticas(conn)
        print("\n=== ESTATISTICAS DJEN MONITOR v2.0 ===")
        print("Total publicacoes:    {}".format(s["total_publicacoes"]))
        print("Nao notificadas:      {}".format(s["nao_notificadas"]))
        print("Monitorados ativos:   {}".format(s["monitorados_ativos"]))
        print("Total buscas:         {}".format(s["total_buscas"]))
        print("Por fonte:            {}".format(json.dumps(s["por_fonte"], indent=2)))
        print("Por tribunal:         {}".format(json.dumps(s["por_tribunal"], indent=2)))
        if s["ultimas_buscas"]:
            print("\nUltimas buscas:")
            for b in s["ultimas_buscas"]:
                print("  {} | {:<15} | {:<8} | {} | {} res | {} | {}ms".format(
                    b[6], b[0] or "N/A", b[1] or "N/A", b[2] or "N/A",
                    b[3], b[4], b[5] or 0))

    elif args.comando == "health":
        print("\n=== VERIFICACAO DE FONTES ===")
        results = health_check_all()
        for r in results:
            status_icon = "OK" if r.get("status") == "ok" else "FALHA"
            print("  [{:5}] {:<20} {}".format(
                status_icon, r.get("source", "?"), r.get("message", "")))

    elif args.comando == "monitor":
        hoje = datetime.now()
        for d in range(args.dias):
            data = (hoje - timedelta(days=d)).strftime("%d/%m/%Y")
            log.info("=== Monitoramento automatico: %s ===", data)
            novos = executar_busca(conn, data_inicio=data, data_fim=data)
            log.info("Total novos para %s: %d", data, novos)

    elif args.comando == "fontes":
        print("\n=== FONTES DISPONIVEIS ===")
        for nome, cls in SOURCES.items():
            source = cls()
            print("\n  {} - {}".format(nome, source.description))
            if hasattr(source, 'listar_tribunais'):
                tribunais = source.listar_tribunais()
                print("    Tribunais: {} disponiveis".format(len(tribunais)))
                print("    Ex: {}".format(", ".join(tribunais[:10])))

    elif args.comando == "parse":
        p = LegalParser()
        resultado = p.extrair_tudo(args.texto)
        print("\n=== ANALISE JURIDICA ===")
        for chave, valores in resultado.items():
            if valores:
                print("  {}: {}".format(chave, json.dumps(valores, ensure_ascii=False, indent=2)))

    elif args.comando == "notif":
        notif_config = NotificationConfig(config_path=CONFIG_DIR / "notifications.json")
        if args.notif_cmd == "add-whatsapp":
            notif_config.add_whatsapp(args.numero)
            print("WhatsApp {} adicionado".format(args.numero))
        elif args.notif_cmd == "add-email":
            notif_config.add_email(args.email)
            print("Email {} adicionado".format(args.email))
        elif args.notif_cmd == "show":
            print(json.dumps(notif_config.config, indent=2, ensure_ascii=False))
        else:
            notif_p.print_help()

    else:
        parser.print_help()

    conn.close()

if __name__ == "__main__":
    main()

