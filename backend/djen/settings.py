"""
Captacao Peticao Blindada - Configuracoes centralizadas.

Carrega variaveis de ambiente com valores padrao seguros.
Uso:
    from djen.settings import settings
    print(settings.CAPTACAO_PORT)
"""

import os
from pathlib import Path

# Tentar carregar .env
try:
    from dotenv import load_dotenv
    # Procura .env na raiz do projeto (2 niveis acima de backend/djen/)
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


class Settings:
    """Configuracoes carregadas de variaveis de ambiente."""

    # --- API Server ---
    CAPTACAO_PORT: int = int(os.environ.get("CAPTACAO_PORT", "8000"))
    CAPTACAO_HOST: str = os.environ.get("CAPTACAO_HOST", "0.0.0.0")

    # --- Database ---
    CAPTACAO_DB_PATH: str = os.environ.get(
        "CAPTACAO_DB_PATH",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "captacao_blindada.db"),
    )

    # --- JWT Auth ---
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

    # --- Admin ---
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "")
    ADMIN_FULL_NAME: str = os.environ.get("ADMIN_FULL_NAME", "Administrador")

    # --- DataJud ---
    DATAJUD_API_KEY: str = os.environ.get("DATAJUD_API_KEY", "")
    DATAJUD_BASE_URL: str = os.environ.get(
        "DATAJUD_BASE_URL",
        "https://api-publica.datajud.cnj.jus.br",
    )

    # --- DJEN ---
    DJEN_API_BASE_URL: str = os.environ.get(
        "DJEN_API_BASE_URL",
        "https://comunicaapi.pje.jus.br",
    )

    # --- Bright Data Proxy ---
    BRIGHT_DATA_CUSTOMER_ID: str = os.environ.get("BRIGHT_DATA_CUSTOMER_ID", "")
    BRIGHT_DATA_PROXY_HOST: str = os.environ.get("BRIGHT_DATA_PROXY_HOST", "brd.superproxy.io")
    BRIGHT_DATA_PROXY_PORT: str = os.environ.get("BRIGHT_DATA_PROXY_PORT", "33335")
    BRIGHT_DATA_PROXY_USERNAME: str = os.environ.get("BRIGHT_DATA_PROXY_USERNAME", "")
    BRIGHT_DATA_PROXY_PASSWORD: str = os.environ.get("BRIGHT_DATA_PROXY_PASSWORD", "")

    # --- ML Agents ---
    USE_ML_AGENTS: bool = os.environ.get("USE_ML_AGENTS", "").lower() in ("true", "1", "yes")
    LLM_API_URL: str = os.environ.get("LLM_API_URL", "")
    LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "gpt-4.1-mini")

    # --- App Info ---
    APP_NAME: str = "Captacao Peticao Blindada"
    APP_VERSION: str = "1.1.0"
    APP_DESCRIPTION: str = "Sistema de captacao e analise de publicacoes judiciais"

    @property
    def proxy_url(self) -> str:
        """Monta URL do proxy Bright Data."""
        if not self.BRIGHT_DATA_PROXY_USERNAME:
            return ""
        return (
            f"http://{self.BRIGHT_DATA_PROXY_USERNAME}"
            f":{self.BRIGHT_DATA_PROXY_PASSWORD}"
            f"@{self.BRIGHT_DATA_PROXY_HOST}"
            f":{self.BRIGHT_DATA_PROXY_PORT}"
        )

    @property
    def proxy_dict(self) -> dict:
        """Dict de proxy para requests."""
        url = self.proxy_url
        if not url:
            return {}
        return {"http": url, "https": url}


settings = Settings()
