# Captação Petição Blindada

Sistema de captação, monitoramento e análise inteligente de publicações judiciais do Poder Judiciário brasileiro — com segurança reforçada de ponta a ponta.

## Arquitetura

```
                                    ┌──────────────────────┐
                                    │      Internet         │
                                    └──────────┬───────────┘
                                               │
                                         :80 / :443
                                               │
                                    ┌──────────▼───────────┐
                                    │   Caddy (Rev. Proxy)  │
                                    │  TLS automático via    │
                                    │  Let's Encrypt +       │
                                    │  Security Headers      │
                                    └────┬────────────┬─────┘
                                         │            │
                                  /api/* │            │ /*
                                         │            │
                          ┌──────────────▼──┐  ┌──────▼──────────────┐
                          │    Backend       │  │     Frontend        │
                          │    FastAPI       │  │     Next.js 15      │
                          │    :8000         │  │     :3000           │
                          │    (interno)     │  │     (interno)       │
                          └───────┬─────────┘  └─────────────────────┘
                                  │
                       ┌──────────┼──────────────┐
                       │          │              │
                ┌──────▼───┐  ┌──▼───────┐  ┌───▼──────────────┐
                │  SQLite   │  │  Cache   │  │  APIs Externas   │
                │ (WAL mode)│  │  L1/L2   │  │  DataJud (CNJ)   │
                └───────────┘  └──────────┘  │  DJEN (CNJ)      │
                                             │  Bright Data      │
                                             └──────────────────┘
```

> Backend e Frontend **não são acessíveis diretamente** — apenas via Caddy nas portas 80/443.

## Stack

| Componente | Tecnologia |
|------------|------------|
| Backend | Python 3.11+ / FastAPI |
| Imagem Docker Backend | `python:3.11-slim-bookworm` |
| Frontend | Next.js 15 / React / Tailwind CSS |
| Runtime Node | Node.js 20+ |
| Autenticação | PyJWT + cookies httpOnly + RBAC |
| Banco de Dados | SQLite (WAL mode, thread-safe) |
| Criptografia | Fernet/AES (`crypto.py`) |
| Reverse Proxy | Caddy (TLS automático via Let's Encrypt) |
| Containers | Docker Compose (non-root, resource limits) |
| Sanitização LLM | `sanitize.py` (prevenção de prompt injection) |

## Funcionalidades

### Backend (FastAPI)
- **120+ endpoints REST** para busca, monitoramento e análise — todos autenticados (`Depends(get_current_user)`)
- **7 fontes de dados** integradas (DataJud, DJEN, TJSP DJe, DEJT, Querido Diário, JusBrasil, e-SAJ)
- **14 agentes de IA** organizados em 6 camadas de análise com proteção contra prompt injection
- **Pipeline multi-agentes** com paralelismo automático e resolução de dependências
- **Captação automatizada** com scheduler individual por regra
- **WebSocket** para progresso em tempo real
- **Cache L1/L2** (memória + SQLite) com TTL e LRU eviction
- **Autenticação JWT** via cookies httpOnly + RBAC por roles
- **Rate limiting** em todos os endpoints (60/min GET, 30/min POST/PUT/DELETE, 5/min exports)
- **API keys criptografadas** no banco (Fernet/AES via `crypto.py`)
- **Isolamento multi-tenant** em todas as queries do banco
- **Busca unificada** em múltiplas fontes simultaneamente
- **Processos Monitorados** com verificação automática DataJud + DJEN (6h)
- **Diff hash-based** de movimentações (detecta novas reais)
- **Filtro por fonte** no backend (query `?fonte=`)

### Frontend (Next.js 15)
- **Dashboard** com estatísticas e busca rápida
- **Análise de processos** com resumo, timeline, riscos e dados completos
- **Busca unificada** com filtros por fonte, tribunal e data
- **Monitor** de publicações com CRUD completo
- **Login** com autenticação JWT (cookies httpOnly)
- **Security headers** (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- **Design responsivo** com Tailwind CSS
- **Resultados clicáveis** com links para processo em todas as abas
- **Paginação** "Carregar mais" em todas as listas
- **Badges de fonte** diferenciados (azul DataJud / âmbar DJEN)
- **Filtro por fonte** nos resultados (DataJud/DJEN/Todas)
- **Tracking lidos/não-lidos** via localStorage
- **Deep links** do Dashboard (`?filter=novos`, `?filter=recente`)
- **Exportação CSV/JSON** dos processos monitorados
- **Validação CNJ** no formulário de adicionar processo
- **Feriados dinâmicos** (cálculo automático de Páscoa)

### Fontes de Dados

| Fonte | Tipo | Dados |
|-------|------|-------|
| **DataJud** (CNJ) | API REST | Metadados processuais de 90+ tribunais |
| **DJEN** (CNJ) | API REST (SSL verificado) | Texto completo de intimações/citações/editais |
| **TJSP DJe** | Web Scraping | Diário de Justiça Eletrônico do TJSP |
| **DEJT** | JSF Scraping | Diário Eletrônico da Justiça do Trabalho |
| **Querido Diário** | API REST | Diários oficiais municipais |
| **JusBrasil** | Web Unlocker | Jurisprudência e processos |
| **e-SAJ** | Playwright + mTLS | Processos do TJSP com certificado digital |

### Sistema Multi-Agentes (14 agentes, 6 camadas)

| Camada | Agentes | Função |
|--------|---------|--------|
| 1 | `validador` | Validação e normalização do número CNJ |
| 2 | `coletor_datajud`, `coletor_djen` | Coleta de dados brutos (paralelo) |
| 3 | `extrator_entidades`, `analisador_movimentacoes`, `extrator_valores` | Extração primária |
| 4 | `classificador_causa`, `analisador_cronologia`, `calculador_prazos` | Análise secundária |
| 5 | `analisador_risco`, `analisador_jurisprudencia`, `validador_conformidade` | Análise avançada |
| 6 | `gerador_resumo`, `previsor_resultado` | Consolidação final |

## Segurança (v3.0.0)

### Autenticação e Autorização
- JWT armazenado em cookies **httpOnly** (não mais em localStorage)
- Biblioteca migrada de `python-jose` para **PyJWT**
- **Todos os 37 routers** protegidos com `Depends(get_current_user)`
- RBAC corrigido em `auth.py` — controle de acesso por roles funcional
- 2FA corrigido (removido `test_secret` hardcoded)
- Validação de schemas reforçada (senha com `min_length`, patterns de role, etc.)

### Proteção de Dados
- **Zero credenciais hardcoded** no código-fonte
- API keys de IA **criptografadas no banco** com Fernet/AES (`crypto.py`)
- **Isolamento multi-tenant** — todas as queries filtram por `tenant_id`
- Mensagens de erro **não vazam detalhes internos**

### Infraestrutura
- Reverse proxy migrado de Nginx para **Caddy** (TLS automático via Let's Encrypt)
- Apenas portas **80/443 expostas** (backend/frontend isolados na rede interna)
- Containers Docker rodam como **non-root** (`USER 1000` / `USER node`)
- **Resource limits** em todos os containers (CPU + memória)
- `security_opt: no-new-privileges` em todos os serviços
- Frontend em modo **read-only** no container
- `.dockerignore` criado para builds mais seguros
- Todas as dependências **pinadas com `==`**

### Proteção de Endpoints
- **Rate limiting global**: 60/min GET, 30/min POST/PUT/DELETE, 5/min exports
- **Security headers** via Caddy: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **CSP** configurado no frontend
- **SSL verification** habilitado no scraping DJEN

### Proteção contra IA
- **Sanitização de inputs LLM** via `sanitize.py` (prevenção de prompt injection)

### DDL e Inicialização
- DDL do banco movido dos request handlers para o **startup da aplicação**

## Instalação Rápida

### Pré-requisitos
- Docker e Docker Compose
- (Opcional para dev local) Python 3.11+ e Node.js 20+

### Setup com Docker (recomendado)

```bash
# Clonar o repositório
git clone https://github.com/SEU-USUARIO/captacao-blindada.git
cd captacao-blindada

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais (veja seção Variáveis de Ambiente)

# Gerar chaves secretas
python -c "import secrets; print(secrets.token_hex(32))"  # para JWT_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # para ENCRYPTION_KEY

# Build e start (Caddy + Backend + Frontend)
docker compose up -d

# Verificar status
docker compose ps

# Logs
docker compose logs -f
```

O Caddy gerencia TLS automaticamente. Em produção, defina `DOMAIN=seudominio.com.br` no `.env`.

### Setup Manual (desenvolvimento)

```bash
# Backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\Activate.ps1  # Windows
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

## Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Obrigatória | Descrição |
|----------|:-----------:|-----------|
| `IS_PRODUCTION` | Sim | `true` em produção, `false` em dev |
| `JWT_SECRET_KEY` | Sim | Chave secreta JWT (mín. 32 chars). Gere com: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ENCRYPTION_KEY` | Sim | Chave Fernet para criptografar API keys no banco. Gere com: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Não altere após salvar keys!** |
| `ADMIN_USERNAME` | Sim | Usuário administrador inicial |
| `ADMIN_PASSWORD` | Sim | Senha do administrador (use senha forte!) |
| `DOMAIN` | Prod | Domínio para TLS automático do Caddy (ex: `app.exemplo.com.br`) |
| `ALLOWED_ORIGINS` | Prod | Origens permitidas para CORS (ex: `https://app.exemplo.com.br`). Separe múltiplas com vírgula. |
| `CAPTACAO_DB_PATH` | — | Caminho do SQLite (padrão: `/app/data/captacao_blindada.db`) |
| `DATAJUD_API_KEY` | — | Chave da API DataJud (CNJ) |
| `BRIGHTDATA_PROXY_URL` | — | Proxy residencial BR para fontes que exigem IP brasileiro |
| `BRIGHTDATA_USERNAME` | — | Usuário do proxy Bright Data |
| `BRIGHTDATA_PASSWORD` | — | Senha do proxy Bright Data |
| `OPENAI_API_KEY` | — | Chave OpenAI para agentes de IA |
| `ANTHROPIC_API_KEY` | — | Chave Anthropic para agentes de IA |
| `WHATSAPP_TOKEN` | — | Token para notificações WhatsApp |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | — | Configuração de e-mail para notificações |

> **Importante:** Nunca commite o arquivo `.env`. Ele já está no `.gitignore`.

## Execução

### Produção (Docker + Caddy)

```bash
# Subir todos os serviços
docker compose up -d

# Arquitetura:
#   Internet → Caddy (:80/:443) → Backend (:8000 interno) / Frontend (:3000 interno)
#   Backend e Frontend NÃO são acessíveis diretamente.

# Acessar:
#   https://seudominio.com.br        → Dashboard
#   https://seudominio.com.br/api/*  → API REST
```

### Desenvolvimento Local

```bash
# Backend
cd backend && uvicorn djen.api.app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (em outro terminal)
cd frontend && npm run dev

# Acessar:
#   API:       http://localhost:8000
#   Swagger:   http://localhost:8000/docs
#   Dashboard: http://localhost:3000
```

## Docker

O `docker-compose.yml` inclui 3 serviços (incluindo Caddy):

| Serviço | Imagem | Porta Exposta | Usuário | Limites |
|---------|--------|:-------------:|---------|---------|
| `caddy` | caddy:2-alpine | 80, 443 | — | 256MB / 0.5 CPU |
| `backend` | python:3.11-slim-bookworm | nenhuma (8000 interno) | `USER 1000` | 1GB / 1.0 CPU |
| `frontend` | node:20-alpine | nenhuma (3000 interno) | `USER node` | 512MB / 0.5 CPU |

Todos os containers possuem `security_opt: no-new-privileges` e o frontend roda em modo read-only.

## Testes

```bash
# Rodar testes
make test

# Com cobertura
make test-cov
```

## Endpoints Principais

> Todos os endpoints (exceto `/api/auth/login` e `/api/metrics/health`) requerem autenticação via cookie JWT.

### Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login (retorna JWT em cookie httpOnly) |
| GET | `/api/auth/me` | Dados do usuário autenticado |
| POST | `/api/auth/refresh` | Renovar token |

### Processo (Análise Multi-Agentes)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/processo/analisar` | Análise completa com pipeline |
| GET | `/api/processo/{numero}` | Processo enriquecido |
| GET | `/api/processo/{numero}/resumo` | Visão executiva |
| GET | `/api/processo/{numero}/timeline` | Timeline interativa |
| GET | `/api/processo/{numero}/riscos` | Indicadores de risco |
| WS | `/api/processo/ws/{numero}` | Progresso em tempo real |

### Captação Automatizada
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/captacao/criar` | Criar captação |
| GET | `/api/captacao/listar` | Listar captações |
| POST | `/api/captacao/{id}/executar` | Executar sob demanda |
| GET | `/api/captacao/{id}/historico` | Histórico de execuções |
| GET | `/api/captacao/{id}/diff` | Comparar execuções |

### Busca
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/datajud/buscar` | Busca no DataJud |
| POST | `/api/djen/buscar` | Busca no DJEN |
| POST | `/api/buscar/unificada` | Busca unificada |

### Monitor
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/monitor/add` | Adicionar monitorado |
| GET | `/api/monitor/list` | Listar monitorados |
| GET | `/api/monitor/stats` | Estatísticas |

### Health Check
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/metrics/health` | Status da aplicação (não requer autenticação) |

## Configuração de Proxy (DJEN)

A API DJEN do CNJ requer IP brasileiro. Para acessar de fora do Brasil:

1. Configure um proxy residencial brasileiro (ex: Bright Data)
2. Preencha as variáveis `BRIGHTDATA_*` no `.env`
3. O sistema usará automaticamente o proxy para requisições ao DJEN

## Estrutura do Projeto

```
captacao-blindada/
├── backend/
│   ├── djen/
│   │   ├── api/
│   │   │   ├── app.py              # App principal + scheduler + DDL no startup
│   │   │   ├── auth.py             # Autenticação JWT (PyJWT) + RBAC
│   │   │   ├── crypto.py           # Criptografia Fernet para API keys
│   │   │   ├── ratelimit.py        # Rate limiting por endpoint
│   │   │   ├── database.py         # SQLite WAL thread-safe + tenant isolation
│   │   │   ├── schemas.py          # Modelos Pydantic (validação reforçada)
│   │   │   ├── resultado_repository.py
│   │   │   └── routers/            # 37 routers (todos autenticados)
│   │   ├── agents/
│   │   │   ├── sanitize.py         # Prevenção de prompt injection
│   │   │   ├── orchestrator.py     # Orquestrador com dependências
│   │   │   ├── specialized.py      # 14 agentes especializados
│   │   │   ├── ml_agents.py        # Agentes ML (opcional)
│   │   │   ├── pipeline_service.py # Facade + cache + tracker
│   │   │   └── captacao_service.py # Service de captação
│   │   ├── sources/                # 7 fontes de dados (SSL verificado)
│   │   ├── tests/                  # Testes automatizados
│   │   └── settings.py             # Configurações centralizadas
│   ├── requirements.txt            # Dependências pinadas (==)
│   └── requirements-dev.txt
├── frontend/                       # Dashboard Next.js 15
│   ├── src/
│   │   ├── app/                    # Páginas (Dashboard, Processos, Busca, Monitor)
│   │   ├── components/             # Componentes reutilizáveis
│   │   └── lib/                    # API client + auth context (cookies httpOnly)
│   └── e2e/                        # Testes E2E (Playwright)
├── Caddyfile                       # Configuração do reverse proxy + security headers
├── docker-compose.yml              # Caddy + Backend + Frontend (non-root, resource limits)
├── Dockerfile.backend              # Imagem backend (python:3.11-slim-bookworm, USER 1000)
├── Dockerfile.frontend             # Imagem frontend (node:20-alpine, USER node, read-only)
├── .dockerignore                   # Exclusões de build
├── .env.example                    # Template de variáveis de ambiente
├── Makefile                        # Comandos úteis
└── .gitignore
```

## Changelog

### v3.0.0 (2026-04-26) — Security Hardening
- Reverse proxy migrado de Nginx para **Caddy** (TLS automático)
- **Todos os 37 routers** protegidos com autenticação
- JWT migrado de localStorage para **cookies httpOnly**
- `python-jose` substituído por **PyJWT**
- Todas as dependências **pinadas com `==`**
- Containers Docker rodam como **non-root** (USER 1000 / USER node)
- `.dockerignore` criado
- **Resource limits** (CPU/memória) em todos os containers
- Caddy adicionado ao docker-compose (apenas portas 80/443 expostas)
- Portas do backend/frontend **não mais expostas** diretamente
- **Zero credenciais hardcoded** no código-fonte
- API keys **criptografadas no banco** (Fernet via `crypto.py`)
- **Rate limiting** em todos os endpoints (60/min GET, 30/min mutações, 5/min exports)
- **Prevenção de prompt injection** para inputs LLM (`sanitize.py`)
- **SSL verification** habilitado no scraping DJEN
- **Security headers** no frontend (CSP, X-Frame-Options, HSTS, etc.)
- RBAC corrigido em `auth.py`
- 2FA corrigido (removido `test_secret` hardcoded)
- Validação de schemas reforçada (password `min_length`, role patterns)
- DDL movido para **startup da aplicação**
- Mensagens de erro **não vazam detalhes internos**
- **Isolamento multi-tenant** em todas as queries do banco
- Novos arquivos: `crypto.py`, `sanitize.py`, `Caddyfile`

### v2.1.0 (2026-04-24) — 31 implementações
- Badges de fonte diferenciados em todas as abas (azul DataJud / âmbar DJEN)
- Resultados e numero_processo clicáveis com Link para /processo
- Paginação "Carregar mais" em captação, monitor, processos e timeline
- Filtro por fonte nos resultados de captação e busca
- Tracking lidos/não-lidos via localStorage
- Deep links do Dashboard (?filter=novos, ?filter=recente)
- Exportação CSV/JSON dos processos monitorados
- Validação CNJ no formulário de adicionar processo
- Feriados BR dinâmicos (não mais hardcoded)
- ESLint configurado com next/core-web-vitals

### v2.0.0 (2026-04-23) — 200 implementações
- Kanban board, notas, templates, heatmap, score, resumo executivo
- 14 agentes IA em 6 camadas
- 7 fontes de dados integradas
- Pipeline multi-agentes com paralelismo
- Captação automatizada com scheduler
- WebSocket para progresso em tempo real

## Licença

Proprietário — Todos os direitos reservados.
