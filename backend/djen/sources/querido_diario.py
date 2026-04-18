"""
Querido Diario API - Open Knowledge Brasil.

API REST para busca em diarios oficiais MUNICIPAIS brasileiros.
Cobre diarios do poder executivo municipal - nao cobre tribunais.

API: https://api.queridodiario.ok.org.br
Docs: https://api.queridodiario.ok.org.br/docs

Util para: buscas de nomes, OAB, empresas em diarios oficiais municipais.
Por exemplo, publicacoes de nomeacoes, licitacoes, decretos que mencionam
advogados ou partes.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests

from .base import BaseSource, PublicacaoResult

log = logging.getLogger("djen.querido_diario")

# Codigos IBGE de capitais para busca padrao
CAPITAIS_IBGE = {
    "sp": "3550308",      # Sao Paulo
    "rj": "3304557",      # Rio de Janeiro
    "bh": "3106200",      # Belo Horizonte
    "bsb": "5300108",     # Brasilia
    "poa": "4314902",     # Porto Alegre
    "ctb": "4106902",     # Curitiba
    "ssa": "2927408",     # Salvador
    "rec": "2611606",     # Recife
    "for": "2304400",     # Fortaleza
    "man": "1302603",     # Manaus
    "bel": "1501402",     # Belem
    "gyn": "5208707",     # Goiania
    "slz": "2111300",     # Sao Luis
    "cam": "3509502",     # Campinas
}


class QueridoDiarioSource(BaseSource):
    """
    Fonte Querido Diario - Diarios oficiais municipais.
    
    API REST publica, sem autenticacao.
    Busca full-text com operadores OpenSearch.
    """

    name = "querido_diario"
    description = "Querido Diario API - Diarios oficiais municipais"

    BASE_URL = "https://api.queridodiario.ok.org.br"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DJenMonitor/1.0",
            "Accept": "application/json",
        })
        self.timeout = self.config.get("timeout", 30)
        self.max_results = self.config.get("max_results", 10)

    def buscar(
        self,
        termo: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
        **kwargs,
    ) -> List[PublicacaoResult]:
        """
        Busca em diarios oficiais municipais.

        Args:
            termo: Texto para buscar
            data_inicio: DD/MM/AAAA
            data_fim: DD/MM/AAAA
            territory_ids: Lista de codigos IBGE (7 digitos)
            cidade: Sigla da cidade (sp, rj, bh, etc.)
        """
        resultados = []

        # Resolver territory_ids
        territory_ids = kwargs.get("territory_ids", [])
        cidade = kwargs.get("cidade")
        if cidade and cidade.lower() in CAPITAIS_IBGE:
            territory_ids = [CAPITAIS_IBGE[cidade.lower()]]

        # Preparar parametros
        params = {
            "querystring": f'"{termo}"',  # Busca exata
            "size": self.max_results,
            "excerpt_size": 1000,
            "number_of_excerpts": 3,
            "sort_by": "descending_date",
        }

        if territory_ids:
            params["territory_ids"] = territory_ids

        if data_inicio:
            iso = self._format_date_iso(data_inicio)
            if iso:
                params["published_since"] = iso

        if data_fim:
            iso = self._format_date_iso(data_fim)
            if iso:
                params["published_until"] = iso

        try:
            self.log.info("[QD] Buscando: '%s' (cidades: %s)", termo,
                          territory_ids or "todas")

            resp = self._request_with_retry(
                "get", f"{self.BASE_URL}/gazettes",
                session=self.session,
                params=params,
                timeout=self.timeout,
            )

            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total_gazettes", 0)
                gazettes = data.get("gazettes", [])

                self.log.info("[QD] %d resultados (total: %d)", len(gazettes), total)

                for g in gazettes:
                    excerpts = g.get("excerpts", [])
                    conteudo_parts = []
                    conteudo_parts.append(f"Diario Oficial: {g.get('territory_name', 'N/A')} ({g.get('state_code', '')})")
                    conteudo_parts.append(f"Data: {g.get('date', 'N/A')}")
                    if g.get("edition"):
                        conteudo_parts.append(f"Edicao: {g['edition']}")
                    if g.get("is_extra_edition"):
                        conteudo_parts.append("(Edicao Extra)")
                    conteudo_parts.append("")
                    for i, exc in enumerate(excerpts, 1):
                        # Limpar tags HTML dos excerpts
                        clean_exc = exc.replace("<b>", "").replace("</b>", "")
                        conteudo_parts.append(f"Trecho {i}:\n{clean_exc}")

                    conteudo = "\n".join(conteudo_parts)

                    # Converter data YYYY-MM-DD para DD/MM/YYYY
                    data_pub = g.get("date", "")
                    try:
                        dt = datetime.strptime(data_pub, "%Y-%m-%d")
                        data_pub = dt.strftime("%d/%m/%Y")
                    except (ValueError, TypeError):
                        pass

                    resultados.append(PublicacaoResult(
                        fonte="querido_diario",
                        tribunal=f"DO-{g.get('territory_name', 'N/A')}",
                        data_publicacao=data_pub,
                        conteudo=conteudo[:5000],
                        url_origem=g.get("url", ""),
                        raw_data=g,
                    ))
            elif resp.status_code == 422:
                self.log.error("[QD] Parametros invalidos: %s", resp.text[:200])
            else:
                self.log.error("[QD] HTTP %d: %s", resp.status_code, resp.text[:200])

        except requests.exceptions.Timeout:
            self.log.error("[QD] Timeout")
        except Exception as e:
            self.log.error("[QD] Erro: %s", e)

        return resultados

    def buscar_cidade(self, nome: str) -> List[Dict]:
        """Busca cidades por nome (para obter territory_id)."""
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/cities",
                params={"city_name": nome},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("cities", [])
        except Exception as e:
            self.log.error("[QD] Erro ao buscar cidade: %s", e)
        return []

    def _get_route_config(self) -> Dict:
        """Querido Diario e API publica sem restricoes."""
        return {
            "route_type": "direct",
            "proxy_url": None,
            "notes": "API publica sem autenticacao ou restricao geografica",
        }

    def health_check(self) -> Dict:
        """Verifica se a API esta disponivel."""
        try:
            resp = self.session.get(f"{self.BASE_URL}/health", timeout=10)
            return {
                "source": "querido_diario",
                "status": "ok" if resp.status_code == 200 else "error",
                "http_code": resp.status_code,
                "message": "API acessivel" if resp.status_code == 200 else f"HTTP {resp.status_code}",
            }
        except Exception as e:
            return {
                "source": "querido_diario",
                "status": "error",
                "message": str(e),
            }
