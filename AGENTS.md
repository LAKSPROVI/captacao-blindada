# AGENTS.md — Captação Petição Blindada

## Visão Geral
Sistema jurídico full-stack para captação, monitoramento e análise inteligente de publicações judiciais do Poder Judiciário brasileiro. Licença proprietária.

## Stack
- **Backend**: Python 3.11+ / FastAPI 0.104.0 / SQLite WAL / APScheduler
- **Frontend**: Next.js 15.1.0 / React 19 / Tailwind CSS 3.4 / Radix UI
- **Auth**: PyJWT + bcrypt + cookies httpOnly + RBAC (5 roles)
- **Proxy**: Caddy 2-alpine (TLS automático Let's Encrypt)
- **Containers**: Docker Compose 3.8 (non-root, resource limits)
- **Testes**: pytest (backend), Playwright (E2E frontend)

## Estrutura de Diretórios
```
backend/djen/api/         → FastAPI app, auth, database, routers (37+)
backend/djen/agents/      → 14 agentes IA em 6 camadas + orquestrador
backend/djen/sources/     → 7 fontes de dados (DataJud, DJEN, TJSP, etc.)
backend/djen/tests/       → Testes unitários backend (16 arquivos)
frontend/src/app/         → Páginas Next.js (dashboard, busca, monitor, etc.)
frontend/src/components/  → 17 componentes React reutilizáveis
frontend/src/lib/         → API client (api.ts), auth context, utils
frontend/src/hooks/       → 4 custom hooks
frontend/e2e/             → Testes E2E Playwright
```

## Comandos Úteis
```bash
# Backend dev
cd backend && uvicorn djen.api.app:app --host 0.0.0.0 --port 8000 --reload

# Frontend dev
cd frontend && npm run dev

# Testes backend
cd backend && python -m pytest djen/tests/ -v --tb=short

# Docker
docker compose build && docker compose up -d

# Makefile
make dev          # Backend dev
make test         # Testes backend
make frontend-dev # Frontend dev
make docker-up    # Containers
```

## Variáveis de Ambiente Obrigatórias
- `JWT_SECRET_KEY` — Chave secreta JWT (obrigatória sempre)
- `ENCRYPTION_KEY` — Chave Fernet para criptografia de API keys no banco
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — Credenciais do admin master
- `DATAJUD_API_KEY` — API key do DataJud (CNJ)
- `IS_PRODUCTION` — "true" em produção (ativa secure cookies)
- `DOMAIN` — Domínio para Caddy TLS

## Padrões do Projeto
- Todas as dependências Python pinadas com `==` em requirements.txt
- Todos os routers protegidos com `Depends(get_current_user)`
- Isolamento multi-tenant em todas as queries (`tenant_id`)
- API keys criptografadas no banco com Fernet (`crypto.py`)
- Sanitização de inputs LLM via `sanitize.py`
- Rate limiting: 60/min GET, 30/min POST/PUT/DELETE, 5/min exports
- Frontend API client em `frontend/src/lib/api.ts` com interceptor 401
- Versão atual: v3.0.0 (definida em `app.py` root endpoint)

## Pontos de Atenção Conhecidos
1. **Thread-safety do orquestrador**: Agentes paralelos compartilham o mesmo `ProcessoCanonical` sem lock — risco de race condition em campos compartilhados
2. **Bloqueio de login em memória**: `_login_attempts` dict em `auth.py` é perdido no restart e não compartilhado entre workers
3. **Admin password sync**: `_init_default_admin()` sobrescreve senha do admin a cada startup com valor do .env
4. **Conexões SQLite sem cleanup**: `threading.local()` cria conexões por thread sem `close()`
5. **Tipagem frontend**: ~20 métodos do ApiClient retornam `Promise<any>` — deveriam ter interfaces tipadas
6. **Testes unitários frontend**: Não existem — apenas E2E com Playwright
7. **Endpoint duplicado**: `/api/buscar/unificada` definido tanto em `app.py` quanto em `routers/busca_unificada.py`

## Correções Aplicadas (2026-05-04)
- `cryptography` pinada de `>=41.0.0` para `==44.0.0` em requirements.txt
- Versão no root endpoint corrigida de "1.0.0" para "3.0.0" em app.py
- Arquivos temporários removidos: `tmp_Dockerfile.frontend`, `tmp_docker-compose.yml`, `tmp_fix_package.py`
- Makefile: path de testes corrigido de `tests/` para `djen/tests/`
- Caddyfile: adicionados headers CSP, Permissions-Policy e X-DNS-Prefetch-Control

## Changelog Resumido
- **v3.0.0** (2026-04-26): Security hardening — Caddy, JWT httpOnly, Fernet, rate limiting
- **v2.1.0** (2026-04-24): 31 melhorias UX — badges, filtros, paginação
- **v2.0.0** (2026-04-23): 200 implementações — agentes IA, fontes, pipeline
