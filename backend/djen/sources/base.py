"""
Base class para fontes de publicacoes judiciais.
"""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional

log = logging.getLogger("djen")


class PublicacaoResult:
    """Resultado padronizado de uma publicacao judicial."""

    def __init__(
        self,
        fonte: str,
        tribunal: str,
        data_publicacao: str,
        conteudo: str,
        numero_processo: Optional[str] = None,
        classe_processual: Optional[str] = None,
        orgao_julgador: Optional[str] = None,
        assuntos: Optional[List[str]] = None,
        movimentos: Optional[List[Dict]] = None,
        url_origem: Optional[str] = None,
        caderno: Optional[str] = None,
        pagina: Optional[str] = None,
        oab_encontradas: Optional[List[str]] = None,
        advogados: Optional[List[str]] = None,
        partes: Optional[List[str]] = None,
        raw_data: Optional[Dict] = None,
    ):
        self.fonte = fonte
        self.tribunal = tribunal
        self.data_publicacao = data_publicacao
        self.conteudo = conteudo
        self.numero_processo = numero_processo
        self.classe_processual = classe_processual
        self.orgao_julgador = orgao_julgador
        self.assuntos = assuntos or []
        self.movimentos = movimentos or []
        self.url_origem = url_origem
        self.caderno = caderno
        self.pagina = pagina
        self.oab_encontradas = oab_encontradas or []
        self.advogados = advogados or []
        self.partes = partes or []
        self.raw_data = raw_data or {}

    @property
    def hash(self) -> str:
        """Hash unico para deduplicacao."""
        content = f"{self.fonte}:{self.tribunal}:{self.data_publicacao}:{self.conteudo[:500]}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "hash": self.hash,
            "fonte": self.fonte,
            "tribunal": self.tribunal,
            "data_publicacao": self.data_publicacao,
            "conteudo": self.conteudo,
            "numero_processo": self.numero_processo,
            "classe_processual": self.classe_processual,
            "orgao_julgador": self.orgao_julgador,
            "assuntos": self.assuntos,
            "movimentos": self.movimentos,
            "url_origem": self.url_origem,
            "caderno": self.caderno,
            "pagina": self.pagina,
            "oab_encontradas": self.oab_encontradas,
            "advogados": self.advogados,
            "partes": self.partes,
        }


class BaseSource(ABC):
    """Classe base para todas as fontes de publicacoes judiciais."""

    name: str = "base"
    description: str = ""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.log = logging.getLogger(f"djen.{self.name}")

    @abstractmethod
    def buscar(
        self,
        termo: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
        **kwargs,
    ) -> List[PublicacaoResult]:
        """
        Busca publicacoes judiciais.

        Args:
            termo: Texto para buscar (nome, OAB, processo, etc.)
            data_inicio: Data inicio formato DD/MM/AAAA
            data_fim: Data fim formato DD/MM/AAAA
            tribunal: Sigla do tribunal (ex: stj, tjsp)

        Returns:
            Lista de PublicacaoResult
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict:
        """Verifica se a fonte esta disponivel."""
        pass

    def _parse_date_br(self, date_str: str) -> Optional[datetime]:
        """Converte DD/MM/AAAA para datetime."""
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except (ValueError, TypeError):
            return None

    def _format_date_iso(self, date_str: str) -> Optional[str]:
        """Converte DD/MM/AAAA ou YYYY-MM-DD para YYYY-MM-DD."""
        if not date_str:
            return None
        # Ja esta em formato ISO — aceita diretamente
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except (ValueError, TypeError):
            pass
        # Converte DD/MM/AAAA
        dt = self._parse_date_br(date_str)
        return dt.strftime("%Y-%m-%d") if dt else None

    def _request_with_retry(
        self,
        method: str,
        url: str,
        session: "requests.Session" = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        **kwargs,
    ):
        """
        Faz request HTTP com retry e exponential backoff.
        Trata HTTP 429 (rate limit) e erros de conexao.

        Args:
            method: 'get' ou 'post'
            url: URL do request
            session: requests.Session (opcional)
            max_retries: Numero maximo de tentativas
            base_delay: Delay inicial em segundos
            max_delay: Delay maximo em segundos
            **kwargs: Argumentos passados para requests (json, data, headers, timeout, etc.)

        Returns:
            requests.Response

        Raises:
            requests.RequestException se todas tentativas falharem
        """
        import requests as req_module

        caller = session or req_module
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                resp = getattr(caller, method.lower())(url, **kwargs)

                # Se recebeu 429, esperar o tempo indicado pelo servidor
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = min(float(retry_after), max_delay)
                        except ValueError:
                            wait_time = min(base_delay * (2 ** attempt), max_delay)
                    else:
                        wait_time = min(base_delay * (2 ** attempt), max_delay)

                    self.log.warning(
                        "[%s] HTTP 429 Rate Limited em %s. Aguardando %.1fs (tentativa %d/%d)",
                        self.name, url[:80], wait_time, attempt + 1, max_retries
                    )
                    time.sleep(wait_time)
                    continue

                # Se recebeu 503 (Service Unavailable), retry
                if resp.status_code == 503 and attempt < max_retries:
                    wait_time = min(base_delay * (2 ** attempt), max_delay)
                    self.log.warning(
                        "[%s] HTTP 503 em %s. Retry em %.1fs (tentativa %d/%d)",
                        self.name, url[:80], wait_time, attempt + 1, max_retries
                    )
                    time.sleep(wait_time)
                    continue

                return resp

            except req_module.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = min(base_delay * (2 ** attempt), max_delay)
                    self.log.warning(
                        "[%s] Timeout em %s. Retry em %.1fs (tentativa %d/%d)",
                        self.name, url[:80], wait_time, attempt + 1, max_retries
                    )
                    time.sleep(wait_time)
                else:
                    self.log.error("[%s] Timeout apos %d tentativas: %s", self.name, max_retries + 1, url[:80])

            except req_module.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = min(base_delay * (2 ** attempt), max_delay)
                    self.log.warning(
                        "[%s] Erro de conexao em %s. Retry em %.1fs (tentativa %d/%d)",
                        self.name, url[:80], wait_time, attempt + 1, max_retries
                    )
                    time.sleep(wait_time)
                else:
                    self.log.error("[%s] Erro de conexao apos %d tentativas: %s", self.name, max_retries + 1, url[:80])

            except req_module.exceptions.RequestException as e:
                last_exception = e
                self.log.error("[%s] Erro de request: %s", self.name, e)
                break

        if last_exception:
            raise last_exception
        return None

    def _get_route_config(self) -> Dict:
        """
        Retorna configuracao de roteamento para esta fonte.
        Pode ser sobrescrito por subclasses para indicar se deve usar VPN, proxy, etc.

        Returns:
            Dict com chaves: route_type ('direct', 'vpn', 'proxy', 'web_unlocker'),
                            proxy_url (se aplicavel), notes
        """
        return {
            "route_type": "direct",
            "proxy_url": None,
            "notes": "Conexao direta (padrao)",
        }
