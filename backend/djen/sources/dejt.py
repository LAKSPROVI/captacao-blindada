"""
DEJT - Diario Eletronico da Justica do Trabalho.

Fonte para publicacoes da Justica do Trabalho (TST, TRTs).
URL: https://dejt.jt.jus.br/dejt/f/n/diariocon

NOTA: Desde agosto de 2024, publicacoes judiciais do PJe migraram
para o DJEN (comunica.pje.jus.br). O DEJT mantem atos administrativos.
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseSource, PublicacaoResult

log = logging.getLogger("djen.dejt")

TRIBUNAIS_TRABALHO = {
    "tst": "0",
    "trt1": "1",
    "trt2": "2",
    "trt3": "3",
    "trt4": "4",
    "trt5": "5",
    "trt6": "6",
    "trt7": "7",
    "trt8": "8",
    "trt9": "9",
    "trt10": "10",
    "trt11": "11",
    "trt12": "12",
    "trt13": "13",
    "trt14": "14",
    "trt15": "15",
    "trt16": "16",
    "trt17": "17",
    "trt18": "18",
    "trt19": "19",
    "trt20": "20",
    "trt21": "21",
    "trt22": "22",
    "trt23": "23",
    "trt24": "24",
    "csjt": "25",
    "enamat": "26",
}


class DEJTSource(BaseSource):
    """
    Fonte DEJT - Diario Eletronico da Justica do Trabalho.
    
    Busca publicacoes administrativas do TST e TRTs.
    Desde ago/2024 publicacoes judiciais PJe migraram para DJEN.
    """

    name = "dejt"
    description = "DEJT - Diario da Justica do Trabalho"

    BASE_URL = "https://dejt.jt.jus.br"
    CONSULTA_URL = "/dejt/f/n/diariocon"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.timeout = self.config.get("timeout", 30)
        self._view_state = None

    def _init_session(self) -> bool:
        """
        Inicializa sessao JSF obtendo ViewState.
        DEJT usa JavaServer Faces - precisa de ViewState para POSTs.
        """
        try:
            url = urljoin(self.BASE_URL, self.CONSULTA_URL)
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                vs_input = soup.find("input", {"name": "javax.faces.ViewState"})
                if vs_input:
                    self._view_state = vs_input.get("value", "")
                    self.log.info("[DEJT] Sessao JSF inicializada (ViewState obtido)")
                    return True
                else:
                    self.log.warning("[DEJT] ViewState nao encontrado no HTML")
            else:
                self.log.error("[DEJT] HTTP %d ao inicializar sessao", resp.status_code)
        except Exception as e:
            self.log.error("[DEJT] Erro ao inicializar sessao: %s", e)
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
        Busca diarios no DEJT.

        O DEJT lista diarios por data/tribunal, nao por texto.
        Apos obter os diarios, baixa PDFs e busca o termo neles.

        Args:
            termo: Texto para buscar nos diarios
            data_inicio: DD/MM/AAAA
            data_fim: DD/MM/AAAA
            tribunal: Sigla tribunal (tst, trt1-trt24)
        """
        resultados = []

        if not self._init_session():
            self.log.error("[DEJT] Nao foi possivel inicializar sessao")
            return resultados

        # Resolver codigo do tribunal
        trib_code = ""
        if tribunal:
            trib_code = TRIBUNAIS_TRABALHO.get(tribunal.lower(), "")

        # Preparar dados JSF
        form_data = {
            "corpo:formulario": "corpo:formulario",
            "corpo:formulario:tipoCaderno": "1",  # Judiciario
            "corpo:formulario:dataIni": data_inicio or datetime.now().strftime("%d/%m/%Y"),
            "corpo:formulario:dataFim": data_fim or (data_inicio or datetime.now().strftime("%d/%m/%Y")),
            "corpo:formulario:tribunal": trib_code,
            "corpo:formulario:botaoAcaoPesquisar": "Pesquisar",
            "javax.faces.ViewState": self._view_state or "",
        }

        try:
            url = urljoin(self.BASE_URL, self.CONSULTA_URL)
            self.log.info("[DEJT] Buscando diarios de %s a %s (tribunal: %s)",
                          data_inicio, data_fim, tribunal or "todos")

            resp = self._request_with_retry(
                "post", url,
                session=self.session,
                data=form_data,
                timeout=self.timeout,
                allow_redirects=True,
            )

            if resp.status_code == 200:
                resultados = self._parse_diarios(resp.text, termo, data_inicio)
                self.log.info("[DEJT] %d resultados encontrados", len(resultados))
            else:
                self.log.error("[DEJT] HTTP %d", resp.status_code)

        except requests.exceptions.Timeout:
            self.log.error("[DEJT] Timeout")
        except Exception as e:
            self.log.error("[DEJT] Erro: %s", e)

        return resultados

    def _parse_diarios(self, html: str, termo: str, data: Optional[str]) -> List[PublicacaoResult]:
        """Parse dos resultados do DEJT."""
        resultados = []
        soup = BeautifulSoup(html, "html.parser")

        # Procurar tabela de resultados
        tabela = soup.find("table", {"class": re.compile(r"rich-table|resultado")}) or \
                 soup.find("table", id=re.compile(r"tabelaResultado|resultado"))

        if tabela:
            rows = tabela.find_all("tr")
            for row in rows[1:]:  # Pular header
                cells = row.find_all("td")
                if len(cells) >= 3:
                    # Tipicamente: Data | Caderno | Tribunal | Link PDF
                    data_pub = cells[0].get_text(strip=True)
                    caderno = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    tribunal_nome = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                    # Link para PDF
                    pdf_link = row.find("a", href=re.compile(r"\.pdf|download|visualizar"))
                    pdf_url = pdf_link.get("href", "") if pdf_link else ""
                    if pdf_url and not pdf_url.startswith("http"):
                        pdf_url = urljoin(self.BASE_URL, pdf_url)

                    conteudo = f"DEJT - {data_pub}\nCaderno: {caderno}\nTribunal: {tribunal_nome}"
                    if pdf_url:
                        conteudo += f"\nPDF: {pdf_url}"

                    resultados.append(PublicacaoResult(
                        fonte="dejt",
                        tribunal=tribunal_nome or "JT",
                        data_publicacao=data_pub or (data or ""),
                        conteudo=conteudo,
                        caderno=caderno,
                        url_origem=pdf_url or f"{self.BASE_URL}{self.CONSULTA_URL}",
                    ))
        else:
            # Fallback: procurar links de download direto
            links = soup.find_all("a", href=re.compile(r"download|pdf|diario", re.I))
            for link in links:
                href = link.get("href", "")
                texto = link.get_text(strip=True)
                if href and len(texto) > 5:
                    if not href.startswith("http"):
                        href = urljoin(self.BASE_URL, href)
                    resultados.append(PublicacaoResult(
                        fonte="dejt",
                        tribunal="JT",
                        data_publicacao=data or datetime.now().strftime("%d/%m/%Y"),
                        conteudo=f"DEJT Diario: {texto}\nURL: {href}",
                        url_origem=href,
                    ))

        return resultados

    def _get_route_config(self) -> Dict:
        """DEJT funciona via conexao direta."""
        return {
            "route_type": "direct",
            "proxy_url": None,
            "notes": "DEJT acessivel diretamente",
        }

    def health_check(self) -> Dict:
        """Verifica se o DEJT esta acessivel."""
        try:
            url = urljoin(self.BASE_URL, self.CONSULTA_URL)
            resp = self.session.get(url, timeout=10)
            has_form = "formulario" in resp.text if resp.status_code == 200 else False
            return {
                "source": "dejt",
                "status": "ok" if resp.status_code == 200 and has_form else "error",
                "http_code": resp.status_code,
                "has_jsf_form": has_form,
                "message": "DEJT acessivel" if resp.status_code == 200 else f"HTTP {resp.status_code}",
            }
        except Exception as e:
            return {
                "source": "dejt",
                "status": "error",
                "message": str(e),
            }
