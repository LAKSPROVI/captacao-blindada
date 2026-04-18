"""
DataJud API (CNJ) - Fonte principal de dados processuais.
API REST baseada em Elasticsearch que cobre TODOS os tribunais brasileiros.

Documentacao: https://datajud-wiki.cnj.jus.br/api-publica/
Endpoint: POST https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests

from .base import BaseSource, PublicacaoResult

log = logging.getLogger("djen.datajud")

# Mapeamento de sigla para alias do DataJud
TRIBUNAIS_DATAJUD = {
    "stj": "api_publica_stj",
    # STF nao disponivel no DataJud publico (retorna 404)
    # "stf": "api_publica_stf",
    "tst": "api_publica_tst",
    "tjsp": "api_publica_tjsp",
    "tjrj": "api_publica_tjrj",
    "tjmg": "api_publica_tjmg",
    "tjrs": "api_publica_tjrs",
    "tjpr": "api_publica_tjpr",
    "tjsc": "api_publica_tjsc",
    "tjba": "api_publica_tjba",
    "tjpe": "api_publica_tjpe",
    "tjce": "api_publica_tjce",
    "tjgo": "api_publica_tjgo",
    "tjdft": "api_publica_tjdft",
    "tjes": "api_publica_tjes",
    "tjpa": "api_publica_tjpa",
    "tjma": "api_publica_tjma",
    "tjmt": "api_publica_tjmt",
    "tjms": "api_publica_tjms",
    "tjal": "api_publica_tjal",
    "tjrn": "api_publica_tjrn",
    "tjpb": "api_publica_tjpb",
    "tjse": "api_publica_tjse",
    "tjpi": "api_publica_tjpi",
    "tjam": "api_publica_tjam",
    "tjro": "api_publica_tjro",
    "tjac": "api_publica_tjac",
    "tjap": "api_publica_tjap",
    "tjrr": "api_publica_tjrr",
    "tjto": "api_publica_tjto",
    "trf1": "api_publica_trf1",
    "trf2": "api_publica_trf2",
    "trf3": "api_publica_trf3",
    "trf4": "api_publica_trf4",
    "trf5": "api_publica_trf5",
    "trf6": "api_publica_trf6",
    "trt1": "api_publica_trt1",
    "trt2": "api_publica_trt2",
    "trt3": "api_publica_trt3",
    "trt4": "api_publica_trt4",
    "trt5": "api_publica_trt5",
    "trt6": "api_publica_trt6",
    "trt7": "api_publica_trt7",
    "trt8": "api_publica_trt8",
    "trt9": "api_publica_trt9",
    "trt10": "api_publica_trt10",
    "trt11": "api_publica_trt11",
    "trt12": "api_publica_trt12",
    "trt13": "api_publica_trt13",
    "trt14": "api_publica_trt14",
    "trt15": "api_publica_trt15",
    "trt16": "api_publica_trt16",
    "trt17": "api_publica_trt17",
    "trt18": "api_publica_trt18",
    "trt19": "api_publica_trt19",
    "trt20": "api_publica_trt20",
    "trt21": "api_publica_trt21",
    "trt22": "api_publica_trt22",
    "trt23": "api_publica_trt23",
    "trt24": "api_publica_trt24",
}

# Tribunais prioritarios para busca quando nenhum e especificado
TRIBUNAIS_PRIORITARIOS = [
    "stj", "tst",
    "tjsp", "tjrj", "tjmg", "tjrs", "tjpr", "tjsc", "tjba",
    "trf1", "trf2", "trf3", "trf4", "trf5",
]


class DatajudSource(BaseSource):
    """
    Fonte DataJud API (CNJ).
    
    A principal API publica de dados processuais do Brasil.
    Cobre todos os tribunais via Elasticsearch.
    
    Busca por: numero de processo, classe processual, orgao julgador, data.
    NAO busca por: nome de parte (dados protegidos) ou OAB.
    Para busca por nome/OAB, use TJSP DJe ou Querido Diario.
    """

    name = "datajud"
    description = "DataJud API (CNJ) - Dados processuais de todos tribunais"

    BASE_URL = "https://api-publica.datajud.cnj.jus.br"
    API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", self.API_KEY)
        self.base_url = self.config.get("base_url", self.BASE_URL)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"APIKey {self.api_key}",
            "Content-Type": "application/json",
        })
        self.timeout = self.config.get("timeout", 45)
        self.max_results = self.config.get("max_results", 20)

    def _get_endpoint(self, tribunal: str) -> str:
        alias = TRIBUNAIS_DATAJUD.get(tribunal.lower())
        if not alias:
            raise ValueError(
                f"Tribunal '{tribunal}' nao encontrado. "
                f"Disponiveis: {', '.join(sorted(TRIBUNAIS_DATAJUD.keys()))}"
            )
        return f"{self.base_url}/{alias}/_search"

    # Mapeamento de classes processuais comuns para codigos CNJ
    CLASSES_PROCESSUAIS = {
        "habeas corpus": 307,
        "hc": 307,
        "mandado de seguranca": 120,
        "ms": 120,
        "acao civil publica": 65,
        "acp": 65,
        "recurso especial": 205,
        "resp": 205,
        "recurso extraordinario": 206,
        "re": 206,
        "agravo de instrumento": 12,
        "ai": 12,
        "apelacao": 198,
        "embargos de declaracao": 49,
        "ed": 49,
        "acao penal": 283,
        "execucao fiscal": 1116,
        "cumprimento de sentenca": 156,
        "procedimento comum civel": 7,
        "juizado especial": 436,
    }

    def _build_query(self, termo: str, data_inicio: Optional[str] = None,
                     data_fim: Optional[str] = None) -> Dict:
        """Constroi query Elasticsearch."""
        must = []

        # Detectar tipo de busca pelo formato do termo
        termo_limpo = termo.strip()

        # Numero de processo CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
        if self._is_processo_cnj(termo_limpo):
            numero = termo_limpo.replace(".", "").replace("-", "")
            must.append({"match": {"numeroProcesso": numero}})
        elif termo_limpo.lower() in self.CLASSES_PROCESSUAIS:
            # Busca por classe processual conhecida (pelo codigo)
            codigo = self.CLASSES_PROCESSUAIS[termo_limpo.lower()]
            must.append({"match": {"classe.codigo": codigo}})
        else:
            # Busca generica - tenta nome da classe e assuntos
            # IMPORTANTE: usar match_phrase em todos os campos para evitar
            # tokenizacao de palavras comuns (de, do, da) que retornam
            # resultados aleatorios (ex: "de" casa com "Vara de Familia")
            should_clauses = [
                {"match_phrase": {"classe.nome": termo_limpo}},
                {"match_phrase": {"assuntos.nome": termo_limpo}},
                {"match_phrase": {"orgaoJulgador.nome": termo_limpo}},
            ]
            # So incluir busca por numero se o termo parece numerico
            termo_digits = termo_limpo.replace(".", "").replace("-", "").replace("/", "")
            if termo_digits.isdigit() and len(termo_digits) >= 5:
                should_clauses.append({"match": {"numeroProcesso": termo_digits}})
            must.append({
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1,
                }
            })

        # Filtro de data
        if data_inicio or data_fim:
            date_range = {}
            if data_inicio:
                iso = self._format_date_iso(data_inicio)
                if iso:
                    date_range["gte"] = iso
            if data_fim:
                iso = self._format_date_iso(data_fim)
                if iso:
                    date_range["lte"] = iso
            if date_range:
                must.append({"range": {"dataAjuizamento": date_range}})

        query = {
            "size": self.max_results,
            "query": {
                "bool": {
                    "must": must
                }
            },
            "sort": [{"dataAjuizamento": {"order": "desc"}}],
        }

        return query

    def _is_processo_cnj(self, termo: str) -> bool:
        """Verifica se o termo e um numero de processo CNJ."""
        import re
        # Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
        padrao = r"^\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}$"
        # Ou formato sem pontuacao: 20 digitos
        padrao2 = r"^\d{20}$"
        return bool(re.match(padrao, termo) or re.match(padrao2, termo))

    def _parse_hit(self, hit: Dict, tribunal: str) -> PublicacaoResult:
        """Converte hit do Elasticsearch para PublicacaoResult."""
        src = hit.get("_source", {})

        # Extrair movimentos recentes (ultimos 5)
        # Alguns tribunais (ex: TJRJ) retornam movimentos como lista de listas
        movimentos_raw = src.get("movimentos", [])
        movimentos = []
        for m in movimentos_raw[-5:]:
            try:
                if isinstance(m, dict):
                    movimentos.append({
                        "codigo": m.get("codigo"),
                        "nome": m.get("nome", ""),
                        "dataHora": m.get("dataHora", ""),
                    })
                elif isinstance(m, list):
                    # TJRJ: movimentos como lista de listas — flatten
                    for sub in m:
                        if isinstance(sub, dict):
                            movimentos.append({
                                "codigo": sub.get("codigo"),
                                "nome": sub.get("nome", ""),
                                "dataHora": sub.get("dataHora", ""),
                            })
                # Ignorar tipos inesperados silenciosamente
            except Exception as e:
                self.log.warning("[DataJud] Erro parseando movimento: %s", e)

        # Construir conteudo textual
        assuntos_raw = src.get("assuntos", [])
        assuntos = []
        for a in assuntos_raw:
            if isinstance(a, dict):
                assuntos.append(a.get("nome", ""))
            elif isinstance(a, str):
                assuntos.append(a)
        assuntos = [a for a in assuntos if a]

        orgao = src.get("orgaoJulgador", {})
        if not isinstance(orgao, dict):
            orgao = {}
        classe = src.get("classe", {})
        if not isinstance(classe, dict):
            classe = {}

        conteudo_parts = []
        conteudo_parts.append(f"Processo: {src.get('numeroProcesso', 'N/A')}")
        conteudo_parts.append(f"Tribunal: {tribunal.upper()}")
        conteudo_parts.append(f"Classe: {classe.get('nome', 'N/A')} ({classe.get('codigo', '')})")
        conteudo_parts.append(f"Orgao Julgador: {orgao.get('nome', 'N/A')}")
        if assuntos:
            conteudo_parts.append(f"Assuntos: {'; '.join(assuntos)}")
        conteudo_parts.append(f"Data Ajuizamento: {src.get('dataAjuizamento', 'N/A')}")
        conteudo_parts.append(f"Grau: {src.get('grau', 'N/A')}")
        formato = src.get("formato", {})
        if isinstance(formato, dict):
            conteudo_parts.append(f"Formato: {formato.get('nome', 'N/A')}")
        if movimentos:
            conteudo_parts.append("Ultimos movimentos:")
            for m in movimentos:
                conteudo_parts.append(f"  [{m['dataHora']}] {m['nome']}")

        conteudo = "\n".join(conteudo_parts)

        # Data publicacao — validar anos razoaveis (1900-2100)
        data_pub = src.get("dataAjuizamento", "")
        if data_pub and "T" in data_pub:
            data_pub = data_pub.split("T")[0]
        # Converter YYYY-MM-DD para DD/MM/YYYY, validando o ano
        try:
            dt = datetime.strptime(data_pub, "%Y-%m-%d")
            if dt.year < 1900 or dt.year > 2100:
                self.log.warning("[DataJud] Data invalida (ano %d): %s", dt.year, data_pub)
                data_pub = "Data indisponivel"
            else:
                data_pub = dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            data_pub = data_pub or "Data indisponivel"

        return PublicacaoResult(
            fonte="datajud",
            tribunal=tribunal.upper(),
            data_publicacao=data_pub,
            conteudo=conteudo,
            numero_processo=src.get("numeroProcesso"),
            classe_processual=classe.get("nome"),
            orgao_julgador=orgao.get("nome"),
            assuntos=assuntos,
            movimentos=movimentos,
            url_origem=f"{self.base_url}/{TRIBUNAIS_DATAJUD.get(tribunal.lower(), '')}/_search",
            raw_data=src,
        )

    def buscar(
        self,
        termo: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
        **kwargs,
    ) -> List[PublicacaoResult]:
        """
        Busca no DataJud.

        Se tribunal nao for especificado, busca nos tribunais prioritarios.
        """
        resultados = []

        tribunais = [tribunal] if tribunal else TRIBUNAIS_PRIORITARIOS
        max_per_tribunal = kwargs.get("max_per_tribunal", 10)

        for trib in tribunais:
            trib_lower = trib.lower()
            if trib_lower not in TRIBUNAIS_DATAJUD:
                self.log.warning("Tribunal '%s' nao disponivel no DataJud", trib)
                continue

            try:
                endpoint = self._get_endpoint(trib_lower)
                query = self._build_query(termo, data_inicio, data_fim)
                query["size"] = max_per_tribunal

                self.log.info("[DataJud] Buscando em %s: '%s'", trib_lower.upper(), termo)

                resp = self._request_with_retry(
                    "post", endpoint,
                    session=self.session,
                    json=query,
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    hits = data.get("hits", {}).get("hits", [])
                    total = data.get("hits", {}).get("total", {}).get("value", 0)
                    self.log.info("[DataJud] %s: %d resultados (total: %d)",
                                  trib_lower.upper(), len(hits), total)

                    for hit in hits:
                        try:
                            result = self._parse_hit(hit, trib_lower)
                            resultados.append(result)
                        except Exception as e:
                            self.log.error("[DataJud] Erro ao parsear hit: %s", e)
                elif resp.status_code == 403:
                    self.log.warning("[DataJud] %s: API Key rejeitada (403)", trib_lower.upper())
                elif resp.status_code == 404:
                    self.log.warning("[DataJud] %s: Endpoint nao encontrado (404)", trib_lower.upper())
                else:
                    self.log.error("[DataJud] %s: HTTP %d - %s",
                                   trib_lower.upper(), resp.status_code,
                                   resp.text[:200])

            except requests.exceptions.Timeout:
                self.log.error("[DataJud] %s: Timeout", trib_lower.upper())
            except requests.exceptions.ConnectionError as e:
                self.log.error("[DataJud] %s: Erro de conexao: %s", trib_lower.upper(), e)
            except Exception as e:
                self.log.error("[DataJud] %s: Erro inesperado: %s", trib_lower.upper(), e)

        self.log.info("[DataJud] Total: %d resultados", len(resultados))
        return resultados

    def buscar_processo(self, numero_processo: str, tribunal: str) -> List[PublicacaoResult]:
        """Busca especifica por numero de processo em um tribunal."""
        return self.buscar(numero_processo, tribunal=tribunal, max_per_tribunal=10)

    def buscar_movimentos_recentes(
        self, tribunal: str, data_inicio: str, data_fim: Optional[str] = None
    ) -> List[PublicacaoResult]:
        """
        Busca movimentos processuais recentes em um tribunal.
        Util para monitoramento de prazos e andamentos.
        """
        data_fim = data_fim or data_inicio
        iso_inicio = self._format_date_iso(data_inicio)
        iso_fim = self._format_date_iso(data_fim)

        if not iso_inicio:
            self.log.error("Data inicio invalida: %s", data_inicio)
            return []

        endpoint = self._get_endpoint(tribunal)
        query = {
            "size": self.max_results,
            "query": {
                "bool": {
                    "must": [
                        {
                            "nested": {
                                "path": "movimentos",
                                "query": {
                                    "range": {
                                        "movimentos.dataHora": {
                                            "gte": iso_inicio,
                                            "lte": iso_fim or iso_inicio,
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [{"dataAjuizamento": {"order": "desc"}}],
        }

        try:
            resp = self._request_with_retry("post", endpoint, session=self.session, json=query, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get("hits", {}).get("hits", [])
                return [self._parse_hit(h, tribunal) for h in hits]
        except Exception as e:
            self.log.error("[DataJud] Erro: %s", e)

        return []

    def listar_tribunais(self) -> List[str]:
        """Lista todos os tribunais disponiveis."""
        return sorted(TRIBUNAIS_DATAJUD.keys())

    def _get_route_config(self) -> Dict:
        """DataJud funciona melhor via VPN (IP brasileiro) ou conexao direta do servidor."""
        return {
            "route_type": "vpn",
            "proxy_url": None,
            "notes": "DataJud responde HTTP 200 com VPN ProtonVPN ativa no servidor",
        }

    def health_check(self) -> Dict:
        """Verifica conectividade com a API."""
        try:
            # Testa com query minima no STJ
            endpoint = self._get_endpoint("stj")
            query = {"size": 1, "query": {"match_all": {}}}
            resp = self._request_with_retry("post", endpoint, session=self.session, json=query, timeout=20, max_retries=2)
            return {
                "source": "datajud",
                "status": "ok" if resp.status_code == 200 else "error",
                "http_code": resp.status_code,
                "message": "API acessivel" if resp.status_code == 200 else f"HTTP {resp.status_code}",
            }
        except Exception as e:
            return {
                "source": "datajud",
                "status": "error",
                "message": str(e),
            }
