"""
Route Manager - Gerenciador de rotas de rede para fontes DJEN.

Seleciona automaticamente a melhor rota (direta, VPN, proxy residencial,
Web Unlocker) para cada fonte/tribunal baseado em configuracao e testes.

Rotas disponiveis:
- direct: Conexao direta do servidor (sem VPN/proxy)
- vpn: Via ProtonVPN split tunnel (protonvpn-split.service)  
- residential_proxy: Via Bright Data proxy residencial brasileiro
- web_unlocker: Via Bright Data Web Unlocker API (resolve Cloudflare)
- scraping_browser: Via Bright Data Scraping Browser (remote CDP)
"""

import json
import logging
import os
import subprocess
from typing import Dict, Optional, List
from pathlib import Path

log = logging.getLogger("djen.route_manager")


# Configuracao de rotas por fonte/alvo
DEFAULT_ROUTES = {
    # Fontes DJEN
    "datajud": {
        "route": "vpn",
        "notes": "DataJud responde HTTP 200 com VPN ProtonVPN",
        "fallback": "direct",
    },
    "tjsp_dje": {
        "route": "direct",
        "notes": "DJe TJSP acessivel diretamente do servidor",
        "fallback": "vpn",
    },
    "dejt": {
        "route": "direct",
        "notes": "DEJT acessivel diretamente",
        "fallback": "vpn",
    },
    "djen_api": {
        "route": "residential_proxy",
        "notes": "DJEN API requer IP brasileiro",
        "fallback": None,
    },
    "querido_diario": {
        "route": "direct",
        "notes": "API publica sem restricoes",
        "fallback": None,
    },
    "jusbrasil": {
        "route": "web_unlocker",
        "notes": "Protegido por Cloudflare Turnstile",
        "fallback": "residential_proxy",
    },
    # Tribunais via browser (e-SAJ, PJe)
    "esaj.tjsp": {
        "route": "vpn",
        "notes": "e-SAJ TJSP funciona com VPN",
        "fallback": "residential_proxy",
    },
    # Alvos bloqueados por Cloudflare/WAF
    "stj": {
        "route": "web_unlocker",
        "notes": "STJ protegido por WAF",
        "fallback": "residential_proxy",
    },
    "stf": {
        "route": "web_unlocker",
        "notes": "STF protegido por WAF",
        "fallback": "residential_proxy",
    },
}

# Configuracao Bright Data
BRIGHTDATA_CONFIG = {
    "residential_proxy": {
        "server": "brd.superproxy.io:33335",
        "username": "brd-customer-hl_9fcf364a-zone-residential_proxy1-country-br",
        "password": "a42i721ykgk9",
    },
    "web_unlocker": {
        "api_url": "https://api.brightdata.com/request",
        "zone": "web_unlocker1",
        "api_key_env": "BRIGHTDATA_API_KEY",
        "api_key_default": "0f906555-d01a-49d7-ae59-4a837ea7b23a",
    },
    "scraping_browser": {
        "ws_endpoint": "wss://brd-customer-hl_9fcf364a-zone-scraping_browser1:gfoho6c9oide@brd.superproxy.io:9222",
    },
}


class RouteManager:
    """Gerenciador de rotas de rede para acesso a tribunais e fontes."""

    def __init__(self, config_path: Optional[str] = None):
        self.routes = dict(DEFAULT_ROUTES)
        self.brightdata = dict(BRIGHTDATA_CONFIG)
        self._vpn_status_cache = None
        
        # Carregar config customizada se existir
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        else:
            # Tentar carregar do local padrao
            for p in [
                "/opt/CAPTAÇÃO BLINDADA/djen/config/routes.json",
                os.path.join(os.path.dirname(__file__), "config", "routes.json"),
            ]:
                if os.path.exists(p):
                    self._load_config(p)
                    break

    def _load_config(self, path: str):
        """Carrega configuracao de rotas de arquivo JSON."""
        try:
            with open(path) as f:
                data = json.load(f)
            if "routes" in data:
                self.routes.update(data["routes"])
            if "brightdata" in data:
                self.brightdata.update(data["brightdata"])
            log.info("[RouteManager] Config carregada de %s", path)
        except Exception as e:
            log.warning("[RouteManager] Erro ao carregar config: %s", e)

    def get_route(self, source_name: str) -> Dict:
        """
        Retorna a rota otima para uma fonte/tribunal.
        
        Args:
            source_name: Nome da fonte (datajud, tjsp_dje, jusbrasil, etc.)
            
        Returns:
            Dict com: route, proxy_config (se aplicavel), notes
        """
        route_config = self.routes.get(source_name, {"route": "direct", "notes": "Padrao"})
        route_type = route_config.get("route", "direct")
        
        result = {
            "route_type": route_type,
            "source": source_name,
            "notes": route_config.get("notes", ""),
            "fallback": route_config.get("fallback"),
            "proxy_config": None,
            "web_unlocker_config": None,
        }
        
        if route_type == "residential_proxy":
            result["proxy_config"] = self._get_residential_proxy_config()
        elif route_type == "web_unlocker":
            result["web_unlocker_config"] = self._get_web_unlocker_config()
        elif route_type == "scraping_browser":
            result["proxy_config"] = {
                "ws_endpoint": self.brightdata["scraping_browser"]["ws_endpoint"],
            }
        
        return result

    def get_playwright_proxy(self, source_name: str) -> Optional[Dict]:
        """
        Retorna config de proxy para Playwright, ou None se rota direta/VPN.
        
        Returns:
            Dict com {server, username, password} ou None
        """
        route = self.get_route(source_name)
        if route["route_type"] == "residential_proxy" and route["proxy_config"]:
            cfg = route["proxy_config"]
            return {
                "server": f"http://{cfg['server']}",
                "username": cfg["username"],
                "password": cfg["password"],
            }
        return None

    def get_requests_proxy(self, source_name: str) -> Optional[Dict]:
        """
        Retorna config de proxy para requests library, ou None.
        
        Returns:
            Dict com {http, https} ou None
        """
        route = self.get_route(source_name)
        if route["route_type"] == "residential_proxy" and route["proxy_config"]:
            cfg = route["proxy_config"]
            proxy_url = f"http://{cfg['username']}:{cfg['password']}@{cfg['server']}"
            return {"http": proxy_url, "https": proxy_url}
        return None

    def get_web_unlocker_config(self, source_name: str) -> Optional[Dict]:
        """Retorna config do Web Unlocker se a rota exigir."""
        route = self.get_route(source_name)
        if route["route_type"] == "web_unlocker":
            return self._get_web_unlocker_config()
        return None

    def _get_residential_proxy_config(self) -> Dict:
        """Retorna config do proxy residencial Bright Data."""
        return dict(self.brightdata.get("residential_proxy", {}))

    def _get_web_unlocker_config(self) -> Dict:
        """Retorna config do Web Unlocker Bright Data."""
        cfg = dict(self.brightdata.get("web_unlocker", {}))
        # Resolver API key de env var ou default
        cfg["api_key"] = os.environ.get(
            cfg.get("api_key_env", "BRIGHTDATA_API_KEY"),
            cfg.get("api_key_default", ""),
        )
        return cfg

    def check_vpn_status(self) -> Dict:
        """
        Verifica se a VPN ProtonVPN esta ativa no servidor.
        
        Returns:
            Dict com: active (bool), service_status, public_ip
        """
        result = {"active": False, "service_status": "unknown", "public_ip": None}
        
        try:
            # Verificar systemd service
            proc = subprocess.run(
                ["systemctl", "is-active", "protonvpn-split"],
                capture_output=True, text=True, timeout=5,
            )
            result["service_status"] = proc.stdout.strip()
            result["active"] = proc.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Provavelmente nao estamos no servidor Linux
            result["service_status"] = "not_available"
        
        self._vpn_status_cache = result
        return result

    def get_all_routes(self) -> List[Dict]:
        """Lista todas as rotas configuradas."""
        routes = []
        for name, config in sorted(self.routes.items()):
            routes.append({
                "source": name,
                "route": config.get("route", "direct"),
                "notes": config.get("notes", ""),
                "fallback": config.get("fallback"),
            })
        return routes

    def update_route(self, source_name: str, route_type: str, notes: str = ""):
        """Atualiza a rota para uma fonte."""
        self.routes[source_name] = {
            "route": route_type,
            "notes": notes or f"Atualizado manualmente",
            "fallback": self.routes.get(source_name, {}).get("fallback"),
        }
        log.info("[RouteManager] Rota de '%s' atualizada para '%s'", source_name, route_type)

    def save_config(self, path: str):
        """Salva configuracao atual em arquivo JSON."""
        data = {
            "routes": self.routes,
            "brightdata": self.brightdata,
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.info("[RouteManager] Config salva em %s", path)

