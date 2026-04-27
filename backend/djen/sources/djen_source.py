"""
DJEN API (CNJ) - Diario de Justica Eletronico Nacional.
API REST publica de comunicacoes processuais (intimacoes, citacoes, editais).

Documentacao Swagger: https://app.swaggerhub.com/apis-docs/cnj/pcp/1.0.0
Endpoint: GET https://comunicaapi.pje.jus.br/api/v1/comunicacao
Frontend: https://comunica.pje.jus.br/consulta

IMPORTANTE: Esta API requer IP brasileiro (retorna 403 de IPs estrangeiros).
           Use proxy residencial BR (Bright Data) ou VPN ProtonVPN.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import certifi
import requests

from .base import BaseSource, PublicacaoResult

log = logging.getLogger("djen.djen_api")


class DjenSource(BaseSource):
    """
    Fonte DJEN API (CNJ) - Diario de Justica Eletronico Nacional.

    API publica que retorna comunicacoes processuais de todos os tribunais
    que publicam via DJEN (intimacoes, citacoes, editais).

    Busca por: numero de processo, OAB, nome de advogado, nome de parte,
              tribunal, orgao julgador, data de disponibilizacao.

    Diferente do DataJud (que retorna metadados processuais), o DJEN retorna
    o TEXTO COMPLETO das publicacoes/comunicacoes processuais.

    ATENCAO: Requer IP brasileiro. Configurar proxy BR no RouteManager.
    """

    name = "djen_api"
    description = "DJEN API (CNJ) - Comunicacoes processuais (intimacoes, citacoes, editais)"

    BASE_URL = "https://comunicaapi.pje.jus.br"
    API_PATH = "/api/v1/comunicacao"
    CERTIDAO_PATH = "/api/v1/comunicacao/{hash}/certidao"

    # Tribunais conhecidos que publicam via DJEN
    TRIBUNAIS_DJEN = [
        "STJ", "TST", "STM", "TSE",
        "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
        "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT",
        "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA",
        "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO",
        "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJTO",
        "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7",
        "TRT8", "TRT9", "TRT10", "TRT11", "TRT12", "TRT13", "TRT14",
        "TRT15", "TRT16", "TRT17", "TRT18", "TRT19", "TRT20",
        "TRT21", "TRT22", "TRT23", "TRT24",
    ]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.base_url = self.config.get("base_url", self.BASE_URL)
        self.timeout = self.config.get("timeout", 45)
        self.max_results = self.config.get("max_results", 100)
        self.session = requests.Session()
        # Use proper SSL verification: env var PROXY_CA_CERT for custom CA, otherwise system certs
        cert_path = os.environ.get("PROXY_CA_CERT", certifi.where())
        self.session.verify = cert_path
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

        # Proxy config (obrigatorio para IPs fora do Brasil)
        self._proxy_config = self.config.get("proxy", None)
        if self._proxy_config:
            self.session.proxies.update(self._proxy_config)

    def _get_proxy_dict(self) -> Optional[Dict]:
        """Retorna proxy dict para requests. Usa config ou RouteManager."""
        if self._proxy_config:
            return self._proxy_config

        # Tentar obter do RouteManager se disponivel
        try:
            from djen.route_manager import RouteManager
            rm = RouteManager()
            proxy = rm.get_requests_proxy("djen_api")
            if proxy:
                return proxy
        except Exception:
            pass

        # Fallback: proxy from environment variable
        proxy_url = os.environ.get("BRIGHTDATA_PROXY_URL", "")
        if not proxy_url:
            log.warning("No proxy available: RouteManager failed and BRIGHTDATA_PROXY_URL not set")
            return {}
        return {"http": proxy_url, "https": proxy_url}

    def _build_params(
        self,
        termo: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
        numero_oab: Optional[str] = None,
        uf_oab: Optional[str] = None,
        nome_advogado: Optional[str] = None,
        nome_parte: Optional[str] = None,
        numero_processo: Optional[str] = None,
        orgao_id: Optional[int] = None,
        meio: Optional[str] = None,
        pagina: int = 0,
        itens_por_pagina: Optional[int] = None,
    ) -> Dict:
        """Constroi parametros de query para a API DJEN."""
        params = {
            "pagina": pagina,
            "itensPorPagina": itens_por_pagina or self.max_results,
        }

        # Datas - converter DD/MM/AAAA para YYYY-MM-DD
        if data_inicio:
            iso = self._format_date_iso(data_inicio)
            if iso:
                params["dataDisponibilizacaoInicio"] = iso
        if data_fim:
            iso = self._format_date_iso(data_fim)
            if iso:
                params["dataDisponibilizacaoFim"] = iso

        # Se nenhuma data especificada, usar ultimos 30 dias
        if "dataDisponibilizacaoInicio" not in params:
            dt_inicio = datetime.now() - timedelta(days=30)
            params["dataDisponibilizacaoInicio"] = dt_inicio.strftime("%Y-%m-%d")
        if "dataDisponibilizacaoFim" not in params:
            params["dataDisponibilizacaoFim"] = datetime.now().strftime("%Y-%m-%d")

        # Tribunal
        if tribunal:
            params["siglaTribunal"] = tribunal.upper()

        # Numero OAB
        if numero_oab:
            params["numeroOab"] = numero_oab
        if uf_oab:
            params["ufOab"] = uf_oab.upper()

        # Nome advogado
        if nome_advogado:
            params["nomeAdvogado"] = nome_advogado

        # Nome parte
        if nome_parte:
            params["nomeParte"] = nome_parte

        # Numero processo
        if numero_processo:
            params["numeroProcesso"] = numero_processo

        # Orgao julgador
        if orgao_id:
            params["orgaoId"] = orgao_id

        # Meio: D = Diario Eletronico, E = Edital
        if meio:
            params["meio"] = meio

        # Auto-detectar tipo de busca pelo termo generico
        if termo and not any([numero_processo, numero_oab, nome_advogado, nome_parte]):
            termo_limpo = termo.strip()

            # Numero de processo CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
            if self._is_processo_cnj(termo_limpo):
                params["numeroProcesso"] = termo_limpo
            # OAB: 123456/SP ou SP123456 (exige UF obrigatoriamente)
            elif self._is_oab(termo_limpo):
                m1 = re.match(r"^(\d{3,6})[/-]([A-Za-z]{2})$", termo_limpo)
                m2 = re.match(r"^([A-Za-z]{2})[/-]?(\d{3,6})$", termo_limpo)
                if m1:
                    params["numeroOab"] = m1.group(1)
                    params["ufOab"] = m1.group(2).upper()
                elif m2:
                    params["ufOab"] = m2.group(1).upper()
                    params["numeroOab"] = m2.group(2)
            # Nome livre: busca por parte (captacao = encontrar clientes sem adv)
            else:
                params["nomeParte"] = termo_limpo

        return params

    def _is_processo_cnj(self, termo: str) -> bool:
        """Verifica se o termo e um numero de processo CNJ."""
        padrao = r"^\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}$"
        padrao2 = r"^\d{20}$"
        return bool(re.match(padrao, termo) or re.match(padrao2, termo))

    def _is_oab(self, termo: str) -> bool:
        """Verifica se o termo e um numero de OAB (exige UF para evitar falso positivo)."""
        # Formato: 123456/SP ou SP123456 — UF obrigatoria
        padrao1 = r"^\d{3,6}[/-][A-Za-z]{2}$"
        padrao2 = r"^[A-Za-z]{2}[/-]?\d{3,6}$"
        return bool(re.match(padrao1, termo.strip()) or re.match(padrao2, termo.strip()))

    def _parse_item(self, item: Dict) -> PublicacaoResult:
        """Converte item da API DJEN para PublicacaoResult."""
        # Extrair advogados
        advogados = []
        oab_list = []
        for dest_adv in item.get("destinatarioadvogados", []):
            adv = dest_adv.get("advogado", {})
            nome = adv.get("nome", "")
            oab = adv.get("numero_oab", "")
            uf = adv.get("uf_oab", "")
            if nome:
                advogados.append(nome)
            if oab and uf:
                oab_list.append(f"{oab}/{uf}")
            elif oab:
                oab_list.append(oab)

        # Extrair partes (destinatarios)
        partes = []
        for dest in item.get("destinatarios", []):
            nome = dest.get("nome", "")
            polo = dest.get("polo", "")
            if nome:
                polo_label = {"A": "Ativo", "P": "Passivo"}.get(polo, polo)
                partes.append(f"{nome} ({polo_label})" if polo_label else nome)

        # Data publicacao
        data_pub = item.get("data_disponibilizacao", "")
        # A API retorna em formatos variados: YYYY-MM-DD ou DD/MM/YYYY
        if data_pub and "-" in data_pub and len(data_pub) == 10:
            try:
                dt = datetime.strptime(data_pub, "%Y-%m-%d")
                data_pub = dt.strftime("%d/%m/%Y")
            except ValueError:
                pass

        # Conteudo textual
        texto = item.get("texto", "")
        conteudo_parts = []
        conteudo_parts.append(f"Processo: {item.get('numeroprocessocommascara', item.get('numero_processo', 'N/A'))}")
        conteudo_parts.append(f"Tribunal: {item.get('siglaTribunal', 'N/A')}")
        conteudo_parts.append(f"Orgao: {item.get('nomeOrgao', 'N/A')}")
        conteudo_parts.append(f"Tipo: {item.get('tipoComunicacao', 'N/A')}")
        conteudo_parts.append(f"Classe: {item.get('nomeClasse', 'N/A')}")
        conteudo_parts.append(f"Meio: {item.get('meiocompleto', item.get('meio', 'N/A'))}")
        conteudo_parts.append(f"Data: {data_pub}")
        if partes:
            conteudo_parts.append(f"Partes: {'; '.join(partes)}")
        if advogados:
            conteudo_parts.append(f"Advogados: {'; '.join(advogados)}")
        if oab_list:
            conteudo_parts.append(f"OABs: {'; '.join(oab_list)}")
        if texto:
            conteudo_parts.append(f"\n--- TEXTO DA COMUNICACAO ---\n{texto}")

        conteudo = "\n".join(conteudo_parts)

        return PublicacaoResult(
            fonte="djen_api",
            tribunal=item.get("siglaTribunal", "N/A"),
            data_publicacao=data_pub,
            conteudo=conteudo,
            numero_processo=item.get("numero_processo") or item.get("numeroprocessocommascara"),
            classe_processual=item.get("nomeClasse"),
            orgao_julgador=item.get("nomeOrgao"),
            url_origem=item.get("link", f"{self.base_url}{self.API_PATH}"),
            oab_encontradas=oab_list,
            advogados=advogados,
            partes=[d.get("nome", "") for d in item.get("destinatarios", [])],
            raw_data=item,
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
        Busca comunicacoes processuais no DJEN.

        Args:
            termo: Texto para buscar (processo CNJ, OAB, nome advogado/parte)
            data_inicio: DD/MM/AAAA
            data_fim: DD/MM/AAAA
            tribunal: Sigla do tribunal (ex: TJSP, TJMA, TRF4)
            **kwargs: Parametros adicionais (numero_oab, uf_oab, nome_parte, etc.)

        Returns:
            Lista de PublicacaoResult com texto completo das comunicacoes
        """
        resultados = []

        params = self._build_params(
            termo=termo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tribunal=tribunal,
            numero_oab=kwargs.get("numero_oab"),
            uf_oab=kwargs.get("uf_oab"),
            nome_advogado=kwargs.get("nome_advogado"),
            nome_parte=kwargs.get("nome_parte"),
            numero_processo=kwargs.get("numero_processo"),
            orgao_id=kwargs.get("orgao_id"),
            meio=kwargs.get("meio"),
            pagina=kwargs.get("pagina", 0),
            itens_por_pagina=kwargs.get("itens_por_pagina"),
        )

        url = f"{self.base_url}{self.API_PATH}"
        proxies = self._get_proxy_dict()

        try:
            self.log.info(
                "[DJEN] Buscando: '%s' tribunal=%s datas=%s a %s",
                termo, tribunal, data_inicio, data_fim,
            )

            resp = self._request_with_retry(
                "get", url,
                session=self.session,
                params=params,
                timeout=self.timeout,
                proxies=proxies,
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                count = data.get("count", 0)
                self.log.info("[DJEN] %d resultados retornados (total: %d)", len(items), count)

                for item in items:
                    try:
                        result = self._parse_item(item)
                        resultados.append(result)
                    except Exception as e:
                        self.log.error("[DJEN] Erro ao parsear item: %s", e)

            elif resp.status_code == 403:
                self.log.error(
                    "[DJEN] HTTP 403 - Acesso negado. "
                    "A API requer IP brasileiro. Configure proxy BR."
                )
            elif resp.status_code == 422:
                self.log.error("[DJEN] HTTP 422 - Parametros invalidos: %s", resp.text[:500])
            elif resp.status_code == 429:
                self.log.warning("[DJEN] HTTP 429 - Rate limit excedido")
            else:
                self.log.error("[DJEN] HTTP %d: %s", resp.status_code, resp.text[:300])

        except requests.exceptions.Timeout:
            self.log.error("[DJEN] Timeout ao acessar API")
        except requests.exceptions.ConnectionError as e:
            self.log.error("[DJEN] Erro de conexao: %s", e)
        except Exception as e:
            self.log.error("[DJEN] Erro inesperado: %s", e)

        self.log.info("[DJEN] Total: %d resultados", len(resultados))
        return resultados

    def buscar_por_processo(
        self, numero_processo: str, tribunal: Optional[str] = None,
        data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
    ) -> List[PublicacaoResult]:
        """Busca comunicacoes de um processo especifico."""
        return self.buscar(
            numero_processo, tribunal=tribunal,
            data_inicio=data_inicio, data_fim=data_fim,
            numero_processo=numero_processo,
        )

    def buscar_por_oab(
        self, numero_oab: str, uf_oab: str,
        data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
    ) -> List[PublicacaoResult]:
        """Busca comunicacoes por numero de OAB."""
        return self.buscar(
            f"OAB {numero_oab}/{uf_oab}", tribunal=tribunal,
            data_inicio=data_inicio, data_fim=data_fim,
            numero_oab=numero_oab, uf_oab=uf_oab,
        )

    def buscar_por_advogado(
        self, nome_advogado: str,
        data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
    ) -> List[PublicacaoResult]:
        """Busca comunicacoes por nome de advogado."""
        return self.buscar(
            nome_advogado, tribunal=tribunal,
            data_inicio=data_inicio, data_fim=data_fim,
            nome_advogado=nome_advogado,
        )

    def buscar_por_parte(
        self, nome_parte: str,
        data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
    ) -> List[PublicacaoResult]:
        """Busca comunicacoes por nome de parte."""
        return self.buscar(
            nome_parte, tribunal=tribunal,
            data_inicio=data_inicio, data_fim=data_fim,
            nome_parte=nome_parte,
        )

    def buscar_paginado(
        self, paginas: int = 5, **kwargs,
    ) -> List[PublicacaoResult]:
        """
        Busca com paginacao automatica.

        Args:
            paginas: Numero maximo de paginas para buscar
            **kwargs: Mesmos parametros de buscar()

        Returns:
            Lista consolidada de todos os resultados
        """
        todos_resultados = []

        for pagina in range(paginas):
            kwargs["pagina"] = pagina
            resultados = self.buscar(**kwargs)

            if not resultados:
                self.log.info("[DJEN] Pagina %d sem resultados, encerrando", pagina)
                break

            todos_resultados.extend(resultados)
            self.log.info("[DJEN] Pagina %d: +%d resultados (total: %d)",
                         pagina, len(resultados), len(todos_resultados))

        return todos_resultados

    def obter_certidao(self, hash_comunicacao: str) -> Optional[bytes]:
        """
        Obtem a certidao PDF de uma comunicacao pelo hash.

        Args:
            hash_comunicacao: Hash da comunicacao (campo 'hash' do item)

        Returns:
            Bytes do PDF ou None se falhar
        """
        url = f"{self.base_url}{self.CERTIDAO_PATH.format(hash=hash_comunicacao)}"
        proxies = self._get_proxy_dict()

        try:
            resp = self._request_with_retry(
                "get", url,
                session=self.session,
                timeout=self.timeout,
                proxies=proxies,
            )
            if resp.status_code == 200:
                self.log.info("[DJEN] Certidao obtida: %d bytes", len(resp.content))
                return resp.content
            else:
                self.log.error("[DJEN] Erro ao obter certidao: HTTP %d", resp.status_code)
        except Exception as e:
            self.log.error("[DJEN] Erro ao obter certidao: %s", e)

        return None

    def listar_tribunais(self) -> List[str]:
        """Lista tribunais conhecidos que publicam via DJEN."""
        return sorted(self.TRIBUNAIS_DJEN)

    def _get_route_config(self) -> Dict:
        """DJEN requer proxy residencial brasileiro (IP BR obrigatorio)."""
        return {
            "route_type": "residential_proxy",
            "proxy_url": None,
            "notes": "DJEN requer IP brasileiro - usar proxy residencial BR",
        }

    def health_check(self) -> Dict:
        """Verifica conectividade com a API DJEN."""
        url = f"{self.base_url}{self.API_PATH}"
        proxies = self._get_proxy_dict()

        # Query minima: 1 resultado do TJMA nos ultimos 365 dias
        params = {
            "pagina": 0,
            "itensPorPagina": 1,
            "siglaTribunal": "TJMA",
            "dataDisponibilizacaoInicio": (
                datetime.now() - timedelta(days=365)
            ).strftime("%Y-%m-%d"),
            "dataDisponibilizacaoFim": datetime.now().strftime("%Y-%m-%d"),
        }

        try:
            resp = self._request_with_retry(
                "get", url,
                session=self.session,
                params=params,
                timeout=20,
                max_retries=2,
                proxies=proxies,
            )

            if resp.status_code == 200:
                data = resp.json()
                count = data.get("count", 0)
                return {
                    "source": "djen_api",
                    "status": "ok",
                    "http_code": 200,
                    "message": f"API acessivel ({count} comunicacoes encontradas)",
                    "proxy_used": bool(proxies),
                }
            elif resp.status_code == 403:
                return {
                    "source": "djen_api",
                    "status": "error",
                    "http_code": 403,
                    "message": "HTTP 403 - IP nao brasileiro. Configurar proxy BR.",
                    "proxy_used": bool(proxies),
                }
            else:
                return {
                    "source": "djen_api",
                    "status": "error",
                    "http_code": resp.status_code,
                    "message": f"HTTP {resp.status_code}",
                    "proxy_used": bool(proxies),
                }
        except Exception as e:
            return {
                "source": "djen_api",
                "status": "error",
                "message": str(e),
                "proxy_used": bool(proxies),
            }
