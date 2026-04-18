"""
JusBrasil - Busca via Bright Data Web Unlocker API.

O Web Unlocker resolve automaticamente Cloudflare Turnstile, CAPTCHAs e
proteções anti-bot. Não requer Playwright nem browser headless.

Cobertura: STF, STJ, TST, todos TJs, TRFs, TRTs, DOU, DOE, DOM
Busca por: nome, OAB, numero de processo, parte, advogado
"""

import json
import os
import re
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from html.parser import HTMLParser

from .base import BaseSource, PublicacaoResult

log = logging.getLogger("djen.jusbrasil")

# ============================================================
# HTML Parser para extrair resultados de diarios
# ============================================================

class JusBrasilDiarioParser(HTMLParser):
    """Parser para extrair resultados de busca de diarios do JusBrasil."""

    def __init__(self):
        super().__init__()
        self.results = []
        self._in_ld_json = False
        self._ld_json_data = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "script" and attrs_dict.get("type") == "application/ld+json":
            self._in_ld_json = True
            self._ld_json_data = ""

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld_json:
            self._in_ld_json = False
            try:
                data = json.loads(self._ld_json_data)
                self._extract_from_ld_json(data)
            except (json.JSONDecodeError, KeyError):
                pass

    def handle_data(self, data):
        if self._in_ld_json:
            self._ld_json_data += data

    def _extract_from_ld_json(self, data):
        """Extrai resultados do JSON-LD da pagina de busca."""
        graphs = data.get("@graph", [data]) if isinstance(data, dict) else data
        for item in graphs:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "ItemList":
                for entry in item.get("itemListElement", []):
                    inner = entry.get("item", entry)
                    if isinstance(inner, dict) and inner.get("@id"):
                        self.results.append({
                            "url": inner.get("@id", ""),
                            "title": inner.get("name", ""),
                            "position": entry.get("position", 0),
                        })


class JusBrasilSource(BaseSource):
    """
    Fonte JusBrasil via Bright Data Web Unlocker API.

    Contorna Cloudflare/Turnstile automaticamente via Web Unlocker.
    Busca em diarios de TODOS os tribunais do Brasil.
    """

    name = "jusbrasil"
    description = "JusBrasil - Diarios de todos tribunais (Web Unlocker)"

    # Bright Data Web Unlocker
    UNLOCKER_URL = "https://api.brightdata.com/request"
    UNLOCKER_ZONE = "web_unlocker1"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.config.get(
            "brightdata_api_key",
            os.environ.get("BRIGHTDATA_API_KEY", "0f906555-d01a-49d7-ae59-4a837ea7b23a"),
        )
        self.email = self.config.get("email", "")
        self.senha = self.config.get("senha", "")
        self.timeout = self.config.get("timeout", 60)

    def _web_unlocker_get(self, url: str) -> Optional[str]:
        """Faz GET via Bright Data Web Unlocker. Retorna HTML ou None."""
        try:
            resp = requests.post(
                self.UNLOCKER_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "zone": self.UNLOCKER_ZONE,
                    "url": url,
                    "country": "br",
                    "format": "raw",
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.text
            else:
                self.log.error("[JusBrasil] Web Unlocker HTTP %d: %s", resp.status_code, resp.text[:200])
                return None
        except requests.RequestException as e:
            self.log.error("[JusBrasil] Web Unlocker erro: %s", e)
            return None

    def _parse_diarios_html(self, html: str) -> List[Dict]:
        """Extrai resultados de diarios do HTML da pagina de busca."""
        results = []

        # Método 1: JSON-LD (mais confiável)
        parser = JusBrasilDiarioParser()
        parser.feed(html)
        if parser.results:
            return parser.results

        # Método 2: Regex no HTML para links de diarios
        pattern = r'href="(https?://www\.jusbrasil\.com\.br/diarios/\d+/[^"]+)"[^>]*>([^<]+)'
        for match in re.finditer(pattern, html):
            url, title = match.groups()
            results.append({"url": url, "title": title.strip(), "position": len(results) + 1})

        return results

    def _extract_content_from_page(self, html: str) -> str:
        """Extrai texto principal de uma pagina de diario."""
        # Remover scripts e styles
        clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:5000]

    def buscar(
        self,
        termo: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tribunal: Optional[str] = None,
        **kwargs,
    ) -> List[PublicacaoResult]:
        """Busca publicacoes nos diarios do JusBrasil via Web Unlocker."""
        resultados = []

        if not self.api_key:
            self.log.error("[JusBrasil] API key Bright Data nao configurada")
            return resultados

        # Construir URL de busca
        # Usa /busca geral (funciona via Web Unlocker) em vez de /diarios/busca
        # que pode estar bloqueado por robots.txt no Bright Data
        encoded_termo = requests.utils.quote(termo)
        urls_to_try = [
            f"https://www.jusbrasil.com.br/diarios/busca?q={encoded_termo}",
            f"https://www.jusbrasil.com.br/busca?q={encoded_termo}",
        ]
        
        date_suffix = ""
        if data_inicio:
            date_suffix += f"&date_start={self._format_date_iso(data_inicio)}"
        if data_fim:
            date_suffix += f"&date_end={self._format_date_iso(data_fim)}"

        self.log.info("[JusBrasil] Buscando via Web Unlocker: '%s'", termo)

        # Tentar URLs na ordem de prioridade
        html = None
        for search_url in urls_to_try:
            full_url = search_url + date_suffix
            self.log.info("[JusBrasil] Tentando: %s", full_url)
            html = self._web_unlocker_get(full_url)
            if html and len(html) > 500 and "bad_endpoint" not in html:
                break
            html = None

        if not html:
            return resultados

        # Extrair resultados da lista
        items = self._parse_diarios_html(html)
        self.log.info("[JusBrasil] %d resultados encontrados na busca", len(items))

        for item in items[:20]:
            url = item.get("url", "")
            title = item.get("title", "")

            # Detectar tribunal no titulo
            tribunal_match = re.search(
                r"(STF|STJ|TST|TJ[A-Z]{2}|TJDFT|TRF\d|TRT\s*\d+|DOU|DOE|DOM|DJ[A-Z]{2})",
                title,
                re.I,
            )
            tribunal_nome = tribunal_match.group(1).upper() if tribunal_match else "JusBrasil"

            # Extrair data do titulo (ex: "DJBA 17/03/2026 - Pag. 59")
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})", title)
            data_pub = date_match.group(1) if date_match else (
                data_inicio or datetime.now().strftime("%d/%m/%Y")
            )

            conteudo = title
            # Opcionalmente buscar conteudo completo da pagina individual
            if url and len(items) <= 5:
                page_html = self._web_unlocker_get(url)
                if page_html:
                    conteudo = self._extract_content_from_page(page_html)

            if len(conteudo) < 30:
                conteudo = title

            resultados.append(PublicacaoResult(
                fonte="jusbrasil",
                tribunal=tribunal_nome,
                data_publicacao=data_pub,
                conteudo=conteudo[:5000],
                url_origem=url,
            ))

        return resultados

    def _get_route_config(self) -> Dict:
        """JusBrasil requer Web Unlocker para contornar Cloudflare."""
        return {
            "route_type": "web_unlocker",
            "proxy_url": "https://api.brightdata.com/request",
            "notes": "Protegido por Cloudflare Turnstile. Usar Bright Data Web Unlocker.",
        }

    def health_check(self) -> Dict:
        """Verifica se o Web Unlocker esta funcionando."""
        try:
            html = self._web_unlocker_get("https://www.jusbrasil.com.br")
            if html and "Jusbrasil" in html and len(html) > 1000:
                return {
                    "source": "jusbrasil",
                    "status": "ok",
                    "method": "web_unlocker",
                    "has_api_key": bool(self.api_key),
                    "message": f"Web Unlocker OK, pagina {len(html)} bytes",
                }
            else:
                return {
                    "source": "jusbrasil",
                    "status": "error",
                    "method": "web_unlocker",
                    "message": f"Resposta inesperada: {(html or '')[:100]}",
                }
        except Exception as e:
            return {
                "source": "jusbrasil",
                "status": "error",
                "method": "web_unlocker",
                "message": str(e),
            }
