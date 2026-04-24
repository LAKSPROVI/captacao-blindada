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

from djen.api.database import get_database, Database
from djen.api.schemas import APIInfoResponse
from pydantic import BaseModel # Defensiva para NameError
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from djen.api.audit import registrar_erro_sistema

# Rate Limiter
from djen.api.ratelimit import limiter

# =========================================================================
# Globals
# =========================================================================
_start_time = time.time()
_scheduler = None  # APScheduler (lazy init)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("captacao")



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
        registrar_erro_sistema("scheduler._run_monitor_cycle", type(e).__name__, str(e), traceback.format_exc())


def _run_processos_datajud_cycle(limite: int = 50):
    """Ciclo secundario para verificacao de movimentacoes de processos ja monitorados."""
    try:
        db = get_database()
        processos = db.processos_para_verificar(limite=limite, horas_intervalo=6)
        if not processos:
            return {"status": "success", "message": "Nenhum processo pendente de verificacao"}

        log.info("[Scheduler] Verificando movimentacoes para %d processos", len(processos))

        from djen.sources.datajud import DatajudSource
        from djen.sources.djen_source import DjenSource
        
        dj_source = DatajudSource()
        djen_source = DjenSource()
        
        atualizados = 0
        for proc in processos:
            numero = proc["numero_processo"]
            tribunal = proc.get("tribunal")
            
            # 1. Verificar DataJud (Metadados/Movimentacoes)
            try:
                dj_res = dj_source.buscar(termo=numero, tribunal=tribunal)
                movs = []
                for r in dj_res:
                    if hasattr(r, "movimentos") and r.movimentos:
                        movs.extend(r.movimentos)
                
                if movs:
                    # Calculate new movimentações
                    existing = db.obter_processo_monitorado(numero)
                    old_count = existing.get("total_movimentacoes", 0) if existing else 0
                    db.atualizar_movimentacoes_processo(numero, movs, tribunal=tribunal)
                    novas = max(0, len(movs) - old_count)
                    status_str = "ok" if novas > 0 else "sem_mudancas"
                    db.registrar_historico_processo(
                        numero, status_str, "datajud", len(movs), novas, 
                        f"Capturadas {len(movs)} movimentacoes ({novas} novas)."
                    )
                    atualizados += 1
                else:
                    db.registrar_historico_processo(numero, "sem_mudancas", "datajud", 0, 0)
            except Exception as e:
                db.registrar_historico_processo(numero, "erro", "datajud", 0, 0, str(e))
                log.error("[Scheduler] Erro DataJud processo %s: %s", numero, e)

            # 2. Verificar DJEN (Publicacoes/Texto)
            try:
                # Busca comunicacoes dos ultimos 30 dias para este processo
                djen_res = djen_source.buscar(termo=numero, tribunal=tribunal)
                if djen_res:
                    for pub in djen_res:
                        db.salvar_publicacao(pub.to_dict())
                    db.registrar_historico_processo(
                        numero, "ok", "djen", len(djen_res), 0,
                        f"Encontradas {len(djen_res)} publicacoes no DJEN."
                    )
                else:
                    db.registrar_historico_processo(numero, "sem_mudancas", "djen", 0, 0)
            except Exception as e:
                db.registrar_historico_processo(numero, "erro", "djen", 0, 0, str(e))
                log.error("[Scheduler] Erro DJEN processo %s: %s", numero, e)

        return {"status": "success", "verificados": len(processos), "atualizados": atualizados}

    except Exception as e:
        log.error("[Scheduler] Erro no ciclo de processos: %s", e)
        registrar_erro_sistema("scheduler._run_processos_datajud_cycle", type(e).__name__, str(e), traceback.format_exc())
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
        registrar_erro_sistema("scheduler._run_captacao_scheduler", type(e).__name__, str(e), traceback.format_exc())


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

        # Verificacao de movimentacoes DataJud (intervalo configuravel)
        db = get_database()
        intervalo = int(db.get_setting("datajud_update_interval_hours", 6))
        
        _scheduler.add_job(
            _run_processos_datajud_cycle,
            "interval",
            hours=intervalo,
            id="processos_datajud_cycle",
            name=f"Verificacao de movimentacoes DataJud ({intervalo}h)",
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


def reschedule_datajud_job(hours: int):
    """Reagenda o job de verificacao do DataJud com novo intervalo."""
    global _scheduler
    if not _scheduler:
        return
        
    try:
        _scheduler.reschedule_job(
            "processos_datajud_cycle",
            trigger="interval",
            hours=hours
        )
        # Atualizar nome para clareza
        _scheduler.modify_job("processos_datajud_cycle", name=f"Verificacao de movimentacoes DataJud ({hours}h)")
        log.info("[Scheduler] Job DataJud reagendado para cada %d horas", hours)
    except Exception as e:
        log.error("[Scheduler] Erro ao reagendar job DataJud: %s", e)


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

    # Init default admin (safe inside lifespan)
    try:
        from djen.api.auth import _init_default_admin
        _init_default_admin()
        log.info("[Startup] Admin default inicializado")
    except Exception as e:
        log.error("[Startup] Erro ao inicializar admin: %s", e)

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

# CORS - Restrito em produção
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)

# Security Headers Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

# Gzip Compression
app.add_middleware(GZipMiddleware, minimum_size=500)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Metrics Middleware
from djen.api.metrics import get_metrics

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
            get_metrics().increment_requests()
            get_metrics().increment_requests_endpoint(request.url.path)
            
            # Auditoria automática para ações de escrita (POST/PUT/DELETE)
            if request.method in ("POST", "PUT", "DELETE") and response.status_code < 400:
                try:
                    from djen.api.audit import registrar_auditoria
                    # Extrair IP
                    ip = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", request.client.host if request.client else "unknown"))
                    # Extrair user_id do token se disponível
                    user_id = None
                    tenant_id = None
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        try:
                            from jose import jwt
                            token = auth_header.split(" ")[1]
                            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                            user_id = payload.get("sub")
                            tenant_id = payload.get("tenant_id")
                        except Exception:
                            pass
                    
                    registrar_auditoria(
                        action=f"{request.method}",
                        entity_type=request.url.path,
                        entity_id=request.method,
                        details={"status_code": response.status_code, "method": request.method, "path": request.url.path},
                        user_id=user_id,
                        tenant_id=tenant_id,
                        ip_address=ip,
                    )
                except Exception:
                    pass  # Não falhar por causa de auditoria
            
            return response
        except Exception as e:
            get_metrics().increment_errors(type(e).__name__)
            raise
        finally:
            duration = (time.time() - start) * 1000
            get_metrics().record_duration(duration)

app.add_middleware(MetricsMiddleware)

# Rate Limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    stack = traceback.format_exc()
    error_msg = str(exc)
    error_type = type(exc).__name__
    
    log.error(f"Global exception caught for {request.url.path}: {error_type} - {error_msg}")
    
    # Tentativa basica de pegar tenant e user. Normally via token, but failing sometimes is just app start
    # Without complex middleware, we leave None for broken requests
    registrar_erro_sistema(
        function_name=f"{request.method} {request.url.path}",
        error_type=error_type,
        error_message=error_msg,
        stack_trace=stack,
        tenant_id=None,
        user_id=None
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. O fato foi devidamente reportado para correcao."}
    )

# Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    stack = traceback.format_exc()
    error_msg = str(exc)
    error_type = type(exc).__name__
    
    log.error(f"Global exception caught for {request.url.path}: {error_type} - {error_msg}")
    
    # Tentativa basica de pegar tenant e user. Normalmente via token, mas falhando as vezes eh apenas app start
    # Sem middleware complexo, deixamos None para requests quebradas
    registrar_erro_sistema(
        function_name=f"{request.method} {request.url.path}",
        error_type=error_type,
        error_message=error_msg,
        stack_trace=stack,
        tenant_id=None,
        user_id=None
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. O fato foi devidamente reportado para correcao."}
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
from djen.api.routers.ai_config import router as ai_config_router
from djen.api.routers.settings import router as settings_router
from djen.api.routers.users import router as users_router
from djen.api.routers.billing import router as billing_router
from djen.api.routers.audit import router as audit_router
from djen.api.routers.errors import router as errors_router
from djen.api.routers.validation import router as validation_router
from djen.api.routers.webhooks import router as webhooks_router
from djen.api.routers.metrics import router as metrics_router
from djen.api.routers.advanced import router as advanced_router
from djen.api.routers.notifications import router as notifications_router

# Auth router (public endpoints: login, etc.)
app.include_router(auth_router)

# Validation router
app.include_router(validation_router)

# Webhooks router
app.include_router(webhooks_router)

# Metrics router
app.include_router(metrics_router)

# Advanced configs router
app.include_router(advanced_router)

# Relatorios router
from djen.api.routers.relatorios import router as relatorios_router
app.include_router(relatorios_router)

# Dashboard router
from djen.api.routers.dashboard import router as dashboard_router
app.include_router(dashboard_router)

# Busca Unificada router
from djen.api.routers.busca_unificada import router as busca_unificada_router
app.include_router(busca_unificada_router)

# Prazos router
from djen.api.routers.prazos import router as prazos_router
app.include_router(prazos_router)

# Favoritos e Tags router
from djen.api.routers.favoritos import router as favoritos_router
app.include_router(favoritos_router)

# Agenda router
from djen.api.routers.agenda import router as agenda_router
app.include_router(agenda_router)

# Contadores router
from djen.api.routers.contadores import router as contadores_router
app.include_router(contadores_router)

# Busca Global router
from djen.api.routers.busca_global import router as busca_global_router
app.include_router(busca_global_router)

# Atividades router
from djen.api.routers.atividades import router as atividades_router
app.include_router(atividades_router)

# Sistema router
from djen.api.routers.sistema import router as sistema_router
app.include_router(sistema_router)

# Notifications router
app.include_router(notifications_router)

# Protected routers
app.include_router(datajud_router)
app.include_router(djen_router)
app.include_router(monitor_router)
app.include_router(health_router)
app.include_router(processo_router)
app.include_router(captacao_router)
app.include_router(processos_monitor_router)
app.include_router(ai_config_router)
app.include_router(settings_router)
app.include_router(users_router)
app.include_router(billing_router)
app.include_router(audit_router)
app.include_router(errors_router)

# Analytics router
from djen.api.routers.analytics import router as analytics_router
app.include_router(analytics_router)

# Extras router
from djen.api.routers.extras import router as extras_router
app.include_router(extras_router)

# Tools router
from djen.api.routers.tools import router as tools_router
app.include_router(tools_router)

# Integracoes router
from djen.api.routers.integracoes import router as integracoes_router
app.include_router(integracoes_router)

# Automacoes router
from djen.api.routers.automacoes import router as automacoes_router
app.include_router(automacoes_router)

# Fontes Config router
from djen.api.routers.fontes_config import router as fontes_config_router
app.include_router(fontes_config_router)

# Kanban router
from djen.api.routers.kanban import router as kanban_router
app.include_router(kanban_router)

# Final Batch V2 router
from djen.api.routers.final_batch import router as final_batch_router
app.include_router(final_batch_router)


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
def busca_unificada(
    termo: str,
    tribunal: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
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
        return source.buscar(termo=termo, tribunal=tribunal, data_inicio=data_inicio, data_fim=data_fim)

    def buscar_djen():
        source = DjenSource()
        return source.buscar(termo=termo, tribunal=tribunal, data_inicio=data_inicio, data_fim=data_fim)

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

