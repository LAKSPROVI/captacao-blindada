#!/usr/bin/env python3
"""
Captacao Peticao Blindada - API REST Principal.

Microservice FastAPI para monitoramento e busca de publicacoes judiciais.
Fontes: DataJud (CNJ), DJEN (CNJ), TJSP DJe, DEJT, Querido Diario.

Execucao:
    uvicorn djen.api.app:app --host 0.0.0.0 --port 8000 --reload
    python -m djen.api.app
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from djen.api.database import Database
from djen.api.schemas import APIInfoResponse

# =========================================================================
# Globals
# =========================================================================
_start_time = time.time()
_database: Optional[Database] = None
_scheduler = None  # APScheduler (lazy init)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("captacao")


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
    return _database


# =========================================================================
# Scheduler
# =========================================================================

def _run_monitor_cycle():
    """Ciclo de monitoramento granular: respeita intervalos e horarios de cada item."""
    try:
        from djen.agents.monitor_service import get_monitor_service
        service = get_monitor_service()
        results = service.executar_todos_pendentes()
        
        if results:
            log.info("[Scheduler] DJEN: %d monitoramentos executados", len(results))
    except Exception as e:
        log.error("[Scheduler] Erro no ciclo DJEN: %s", e)


def _run_processos_datajud_cycle(limite: int = 50):
    """Ciclo secundario para verificacao de movimentacoes de processos ja monitorados."""
    try:
        db = get_database()
        processos = db.processos_para_verificar(limite=limite, horas_intervalo=6)
        if not processos:
            return {"status": "success", "message": "Nenhum processo pendente de verificacao"}

        log.info("[Scheduler] Verificando movimentacoes para %d processos", len(processos))

        from djen.sources.datajud import DatajudSource
        source = DatajudSource()
        
        atualizados = 0
        for proc in processos:
            try:
                resultados = source.buscar(termo=proc["numero_processo"], tribunal=proc.get("tribunal"))
                if resultados:
                    # DataJudSource retorna PublicacaoResult, mas para processo pegamos movimentos
                    movs = []
                    # O DataJudSource geralmente coloca o JSON bruto ou lista de movimentos no atributo customizado ou conteudo
                    # Assumindo que o source ja traz os movimentos estruturados se disponivel
                    for r in resultados:
                        if hasattr(r, 'movimentos') and r.movimentos:
                            movs.extend(r.movimentos)
                    
                    if movs:
                        db.atualizar_movimentacoes_processo(
                            proc["numero_processo"],
                            movs,
                            tribunal=proc.get("tribunal")
                        )
                        atualizados += 1
            except Exception as e:
                log.error("[Scheduler] Erro verificando processo %s: %s", proc["numero_processo"], e)

        return {"status": "success", "verificados": len(processos), "atualizados": atualizados}

    except Exception as e:
        log.error("[Scheduler] Erro no ciclo de processos: %s", e)
        return {"status": "error", "message": str(e)}


def _run_captacao_scheduler():
    """Scheduler inteligente: verifica captacoes pendentes a cada 5 minutos."""
    try:
        from djen.agents.captacao_service import get_captacao_service
        service = get_captacao_service()
        results = service.executar_todas()
        total = len(results)
        if total > 0:
            log.info("[Scheduler] Captacao: %d captacoes executadas", total)
    except Exception as e:
        log.error("[Scheduler] Erro no ciclo de captacao: %s", e)


def start_scheduler():
    """Inicia APScheduler para monitoramento periodico."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

        # Monitoramento DJEN Granular a cada 10 minutos
        _scheduler.add_job(
            _run_monitor_cycle,
            "interval",
            minutes=10,
            id="monitor_cycle",
            name="Ciclo de monitoramento DJEN granular (10m)",
            replace_existing=True,
        )

        # Verificacao de movimentacoes DataJud a cada 6 horas (para processos ja registrados)
        _scheduler.add_job(
            _run_processos_datajud_cycle,
            "interval",
            hours=6,
            id="processos_datajud_cycle",
            name="Verificacao de movimentacoes DataJud (6h)",
            replace_existing=True,
        )

        # Captacao inteligente a cada 30 minutos
        _scheduler.add_job(
            _run_captacao_scheduler,
            "interval",
            minutes=30,
            id="captacao_cycle",
            name="Ciclo de captacao inteligente (30m)",
            replace_existing=True,
        )

        _scheduler.start()
        log.info("[Scheduler] Iniciado - Monitor Unificado (1h), Processos (6h), Captacao (30m)")
    except ImportError:
        log.warning("[Scheduler] APScheduler nao instalado. Monitoramento automatico desativado.")
        log.warning("[Scheduler] Instale com: pip install apscheduler")
    except Exception as e:
        log.error("[Scheduler] Erro ao iniciar: %s", e)


# =========================================================================
# Lifespan
# =========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicacao."""
    log.info("=" * 60)
    log.info("  CAPTACAO PETICAO BLINDADA v1.0.0")
    log.info("  Monitoramento de Publicacoes Judiciais")
    log.info("=" * 60)

    # Init database
    get_database()
    log.info("[Startup] Database inicializado")

    # Init scheduler
    start_scheduler()

    yield

    # Shutdown
    if _scheduler and hasattr(_scheduler, "shutdown"):
        _scheduler.shutdown(wait=False)
        log.info("[Shutdown] Scheduler parado")
    log.info("[Shutdown] Captacao Peticao Blindada encerrado")


# =========================================================================
# FastAPI App
# =========================================================================

app = FastAPI(
    title="Captacao Peticao Blindada",
    description=(
        "API de monitoramento e busca de publicacoes judiciais do Poder Judiciario brasileiro.\n\n"
        "## Fontes\n"
        "- **DataJud** (CNJ) - Metadados processuais de 90+ tribunais\n"
        "- **DJEN** (CNJ) - Texto completo de intimacoes, citacoes e editais\n\n"
        "## Funcionalidades\n"
        "- Busca por numero de processo, OAB, nome de advogado/parte\n"
        "- Monitoramento automatico com scheduler\n"
        "- Health check de todas as fontes\n"
        "- Banco SQLite local para historico\n"
        "- **Sistema Multi-Agentes** para analise inteligente de processos\n"
        "- Pipeline com 14 agentes especializados\n"
        "- WebSocket para progresso em tempo real\n"
        "- Cache em memoria para performance\n\n"
        "## Integracao\n"
        "Projetado para funcionar como microservice dentro do CAPTAÇÃO BLINDADA, "
        "acessivel pelo OpenClaw Gateway via HTTP."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# Routers
# =========================================================================

from djen.api.auth import router as auth_router
from djen.api.routers.datajud import router as datajud_router
from djen.api.routers.djen_router import router as djen_router
from djen.api.routers.monitor import router as monitor_router
from djen.api.routers.health import router as health_router
from djen.api.routers.processo import router as processo_router
from djen.api.routers.captacao import router as captacao_router
from djen.api.routers.processos_monitor import router as processos_monitor_router

# Auth router (public endpoints: login, etc.)
app.include_router(auth_router)

# Protected routers
app.include_router(datajud_router)
app.include_router(djen_router)
app.include_router(monitor_router)
app.include_router(health_router)
app.include_router(processo_router)
app.include_router(captacao_router)
app.include_router(processos_monitor_router)


# =========================================================================
# Root
# =========================================================================

@app.get("/", response_model=APIInfoResponse, tags=["Info"])
def root():
    """Informacoes da API Captacao Peticao Blindada."""
    return APIInfoResponse(
        fontes_disponiveis=["datajud", "djen_api", "tjsp_dje", "dejt", "querido_diario"],
    )


@app.post("/api/buscar/unificada", tags=["Busca Unificada"], summary="Busca em multiplas fontes")
def busca_unificada(termo: str, tribunal: Optional[str] = None):
    """
    Busca unificada em DataJud + DJEN simultaneamente.
    Retorna resultados combinados de metadados processuais + comunicacoes.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from djen.sources.datajud import DatajudSource
    from djen.sources.djen_source import DjenSource

    db = get_database()
    resultados = {}
    t0 = time.time()

    def buscar_datajud():
        source = DatajudSource()
        return source.buscar(termo=termo, tribunal=tribunal)

    def buscar_djen():
        source = DjenSource()
        return source.buscar(termo=termo, tribunal=tribunal)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(buscar_datajud): "datajud",
            executor.submit(buscar_djen): "djen_api",
        }
        for future in as_completed(futures, timeout=60):
            nome = futures[future]
            try:
                pubs = future.result()
                for pub in pubs:
                    db.salvar_publicacao(pub.to_dict())
                resultados[nome] = {
                    "total": len(pubs),
                    "resultados": [pub.to_dict() for pub in pubs[:20]],
                }
            except Exception as e:
                resultados[nome] = {"total": 0, "erro": str(e), "resultados": []}

    elapsed = int((time.time() - t0) * 1000)
    total = sum(r.get("total", 0) for r in resultados.values())

    return {
        "status": "success",
        "termo": termo,
        "tribunal": tribunal,
        "total_geral": total,
        "tempo_total_ms": elapsed,
        "resultados_por_fonte": resultados,
    }


# =========================================================================
# Entrypoint
# =========================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("CAPTACAO_PORT", 8000))
    host = os.environ.get("CAPTACAO_HOST", "0.0.0.0")
    uvicorn.run(
        "djen.api.app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )

