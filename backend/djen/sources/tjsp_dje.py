"""
TJSP DJe - Diario de Justica Eletronico do Tribunal de Justica de Sao Paulo.

Busca avancada por texto nas publicacoes do DJe TJSP.
URL: https://dje.tjsp.jus.br/cdje/consultaAvancada.do

Esta e a fonte mais completa para busca textual (nome, OAB, processo)
no maior tribunal estadual do Brasil.
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseSource, PublicacaoResult

log = logging.getLogger("djen.tjsp_dje")

# Cadernos do DJe TJSP
CADERNOS_TJSP = {
    "": "Todos os cadernos",
    "1": "Administrativo",
    "12": "Judicial 2a Instancia - Entrada/Distribuicao",
    "22": "Judicial 2a Instancia - Processamento",
    "13": "Judicial 1a Instancia Capital - Parte I",
    "23": "Judicial 1a Instancia Capital - Parte II",
    "14": "Judicial 1a Instancia Interior - Parte I",
    "24": "Judicial 1a Instancia Interior - Parte II",
    "34": "Judicial 1a Instancia Interior - Parte III",
    "5": "Editais e Leiloes",
}


class TJSPDjeSource(BaseSource):
    """
    Fonte DJe TJSP - Diario de Justica Eletronico de Sao Paulo.
    
    Busca avancada por palavras-chave, data, caderno.
    Suporta busca por: nome, OAB, numero de processo, parte.
    """

    name = "tjsp_dje"
    description = "DJe TJSP - Diario de Justica de Sao Paulo"

    BASE_URL = "https://dje.tjsp.jus.br"
    CONSULTA_AVANCADA = "/cdje/consultaAvancada.do"
    CONSULTA_SIMPLES = "/cdje/consultaSimples.do"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://dje.tjsp.jus.br/cdje/consultaAvancada.do",
    }

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.timeout = self.config.get("timeout", 30)

    def _init_session(self):
        """Inicializa sessao obtendo cookies."""
        try:
            resp = self.session.get(
                urljoin(self.BASE_URL, self.CONSULTA_AVANCADA),
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                self.log.info("[TJSP] Sessao inicializada")
                return True
        except Exception as e:
            self.log.error("[TJSP] Erro ao inicializar sessao: %s", e)
        return False

    def buscar(
        self,
        termo: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
        **kwargs,
    ) -> List[PublicacaoResult]:
        """
        Busca avancada no DJe TJSP.

        Args:
            termo: Texto para buscar (nome, OAB, processo)
            data_inicio: DD/MM/AAAA
            data_fim: DD/MM/AAAA
            caderno: Codigo do caderno (ver CADERNOS_TJSP)
        """
        resultados = []
        caderno = kwargs.get("caderno", "")

        # Inicializar sessao
        self._init_session()

        # Preparar dados do formulario
        # A busca avancada aceita:
        # - palavraConjunta: todas as palavras (AND)
        # - palavraQualquer: qualquer palavra (OR)  
        # - palavraExata: frase exata
        # - palavraSem: palavras excluidas
        form_data = {
            "dadosConsulta.dtInicio": data_inicio or "",
            "dadosConsulta.dtFim": data_fim or (data_inicio or ""),
            "dadosConsulta.cdCaderno": caderno,
        }

        # Decidir tipo de busca baseado no formato do termo
        if self._is_exact_match(termo):
            form_data["dadosConsulta.pesquisaLivre"] = termo
        else:
            form_data["dadosConsulta.pesquisaLivre"] = termo

        url = urljoin(self.BASE_URL, self.CONSULTA_AVANCADA)

        try:
            self.log.info("[TJSP] Buscando: '%s' de %s a %s", termo, data_inicio, data_fim)

            resp = self._request_with_retry(
                "post", url,
                session=self.session,
                data=form_data,
                timeout=self.timeout,
                allow_redirects=True,
            )

            if resp.status_code == 200:
                resultados = self._parse_results(resp.text, termo, data_inicio)
                self.log.info("[TJSP] %d resultados encontrados", len(resultados))
            else:
                self.log.error("[TJSP] HTTP %d", resp.status_code)

        except requests.exceptions.Timeout:
            self.log.error("[TJSP] Timeout")
        except Exception as e:
            self.log.error("[TJSP] Erro: %s", e)

        return resultados

    def _parse_results(self, html: str, termo: str, data: Optional[str]) -> List[PublicacaoResult]:
        """Extrai resultados do HTML de resposta."""
        resultados = []
        soup = BeautifulSoup(html, "html.parser")

        # Tentar varios seletores possiveis
        # O DJe TJSP pode usar diferentes estruturas
        containers = soup.select(
            ".resultadoConsulta, "
            ".itemResultado, "
            ".resultado-item, "
            "div.secaoPublicacao, "
            "tr.publicacao, "
            ".conteudoPublicacao, "
            "div[class*='resultado'], "
            "div[class*='publicacao']"
        )

        if containers:
            for container in containers:
                texto = container.get_text(separator=" ", strip=True)
                if len(texto) > 30 and termo.lower() in texto.lower():
                    # Tentar extrair metadados
                    caderno_el = container.select_one(".caderno, .nomeCaderno")
                    pagina_el = container.select_one(".pagina, .numeroPagina")
                    data_el = container.select_one(".data, .dataPublicacao")

                    caderno = caderno_el.get_text(strip=True) if caderno_el else None
                    pagina = pagina_el.get_text(strip=True) if pagina_el else None
                    data_pub = data_el.get_text(strip=True) if data_el else (data or "")

                    resultados.append(PublicacaoResult(
                        fonte="tjsp_dje",
                        tribunal="TJSP",
                        data_publicacao=data_pub,
                        conteudo=texto[:5000],
                        caderno=caderno,
                        pagina=pagina,
                        url_origem=f"{self.BASE_URL}{self.CONSULTA_AVANCADA}",
                    ))
        else:
            # Fallback: buscar no texto bruto da pagina
            page_text = soup.get_text(separator="\n", strip=True)
            blocos = re.split(r"\n{2,}", page_text)
            for bloco in blocos:
                if len(bloco) > 50 and termo.lower() in bloco.lower():
                    resultados.append(PublicacaoResult(
                        fonte="tjsp_dje",
                        tribunal="TJSP",
                        data_publicacao=data or datetime.now().strftime("%d/%m/%Y"),
                        conteudo=bloco[:5000],
                        url_origem=f"{self.BASE_URL}{self.CONSULTA_AVANCADA}",
                    ))

        return resultados

    def _is_exact_match(self, termo: str) -> bool:
        """Verifica se o termo deve ser buscado como frase exata."""
        # OAB: formato NNN/UF ou NNNNNN/UF
        if re.match(r"^\d{3,6}/[A-Z]{2}$", termo.upper()):
            return True
        # Numero processo CNJ
        if re.match(r"^\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}$", termo):
            return True
        return False

    def buscar_por_caderno(self, caderno: str, data: str) -> List[PublicacaoResult]:
        """Lista publicacoes de um caderno especifico em uma data."""
        self._init_session()
        
        form_data = {
            "dadosConsulta.dtInicio": data,
            "dadosConsulta.dtFim": data,
            "dadosConsulta.cdCaderno": caderno,
        }

        try:
            resp = self.session.post(
                urljoin(self.BASE_URL, self.CONSULTA_SIMPLES),
                data=form_data,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return self._parse_results(resp.text, "", data)
        except Exception as e:
            self.log.error("[TJSP] Erro: %s", e)

        return []

    def _get_route_config(self) -> Dict:
        """DJe TJSP funciona via conexao direta ou VPN."""
        return {
            "route_type": "direct",
            "proxy_url": None,
            "notes": "DJe TJSP acessivel diretamente do servidor",
        }

    def health_check(self) -> Dict:
        """Verifica se o DJe TJSP esta acessivel."""
        try:
            resp = self.session.get(
                urljoin(self.BASE_URL, self.CONSULTA_AVANCADA),
                timeout=10,
            )
            return {
                "source": "tjsp_dje",
                "status": "ok" if resp.status_code == 200 else "error",
                "http_code": resp.status_code,
                "message": "DJe TJSP acessivel" if resp.status_code == 200 else f"HTTP {resp.status_code}",
            }
        except Exception as e:
            return {
                "source": "tjsp_dje",
                "status": "error",
                "message": str(e),
            }
