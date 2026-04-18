# Captacao Peticao Blindada

Sistema de captacao, monitoramento e analise inteligente de publicacoes judiciais do Poder Judiciario brasileiro.

## Funcionalidades

### Backend (FastAPI)
- **45+ endpoints REST** para busca, monitoramento e analise
- **7 fontes de dados** integradas (DataJud, DJEN, TJSP DJe, DEJT, Querido Diario, JusBrasil, e-SAJ)
- **14 agentes de IA** organizados em 6 camadas de analise
- **Pipeline multi-agentes** com paralelismo automatico e resolucao de dependencias
- **Captacao automatizada** com scheduler individual por regra
- **WebSocket** para progresso em tempo real
- **Cache L1/L2** (memoria + SQLite) com TTL e LRU eviction
- **Autenticacao JWT** com controle de acesso por roles
- **Busca unificada** em multiplas fontes simultaneamente

### Frontend (Next.js 15)
- **Dashboard** com estatisticas e busca rapida
- **Analise de processos** com resumo, timeline, riscos e dados completos
- **Busca unificada** com filtros por fonte, tribunal e data
- **Monitor** de publicacoes com CRUD completo
- **Login** com autenticacao JWT
- **Design responsivo** com Tailwind CSS

### Fontes de Dados

| Fonte | Tipo | Dados |
|-------|------|-------|
| **DataJud** (CNJ) | API REST | Metadados processuais de 90+ tribunais |
| **DJEN** (CNJ) | API REST | Texto completo de intimacoes/citacoes/editais |
| **TJSP DJe** | Web Scraping | Diario de Justica Eletronico do TJSP |
| **DEJT** | JSF Scraping | Diario Eletronico da Justica do Trabalho |
| **Querido Diario** | API REST | Diarios oficiais municipais |
| **JusBrasil** | Web Unlocker | Jurisprudencia e processos |
| **e-SAJ** | Playwright + mTLS | Processos do TJSP com certificado digital |

### Sistema Multi-Agentes (14 agentes, 6 camadas)

| Camada | Agentes | Funcao |
|--------|---------|--------|
| 1 | `validador` | Validacao e normalizacao do numero CNJ |
| 2 | `coletor_datajud`, `coletor_djen` | Coleta de dados brutos (paralelo) |
| 3 | `extrator_entidades`, `analisador_movimentacoes`, `extrator_valores` | Extracao primaria |
| 4 | `classificador_causa`, `analisador_cronologia`, `calculador_prazos` | Analise secundaria |
| 5 | `analisador_risco`, `analisador_jurisprudencia`, `validador_conformidade` | Analise avancada |
| 6 | `gerador_resumo`, `previsor_resultado` | Consolidacao final |

## Instalacao Rapida

### Pre-requisitos
- Python 3.10+
- Node.js 18+ (para o frontend)
- pip

### Setup

```bash
# Clonar o repositorio
git clone https://github.com/SEU-USUARIO/captacao-blindada.git
cd captacao-blindada

# Setup automatico
# Linux/macOS:
bash scripts/setup.sh

# Windows (PowerShell):
.\scripts\setup.ps1

# Ou manual:
python -m venv venv
source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\Activate.ps1  # Windows

pip install -r backend/requirements.txt
cp .env.example .env
# Edite .env com suas credenciais

cd frontend && npm install && cd ..
```

### Execucao

```bash
# Backend (API)
make dev
# ou: cd backend && uvicorn djen.api.app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Dashboard)
make frontend-dev
# ou: cd frontend && npm run dev

# Acessar:
# API:       http://localhost:8000
# Swagger:   http://localhost:8000/docs
# Dashboard: http://localhost:3000
# Login:     admin / admin (mude no .env!)
```

### Docker

```bash
# Build e start
docker compose up -d

# Logs
docker compose logs -f

# Parar
docker compose down
```

## Testes

```bash
# Rodar testes
make test

# Com cobertura
make test-cov
```

## Estrutura do Projeto

```
captacao-blindada/
├── backend/
│   ├── djen/
│   │   ├── api/                  # API REST (FastAPI)
│   │   │   ├── app.py            # App principal + scheduler
│   │   │   ├── auth.py           # Autenticacao JWT
│   │   │   ├── database.py       # SQLite WAL thread-safe
│   │   │   ├── schemas.py        # Modelos Pydantic (17+ schemas)
│   │   │   ├── resultado_repository.py  # Persistencia de analises
│   │   │   └── routers/
│   │   │       ├── captacao.py   # Captacao automatizada (15 endpoints)
│   │   │       ├── datajud.py    # Busca no DataJud
│   │   │       ├── djen_router.py # Busca no DJEN
│   │   │       ├── health.py     # Health check
│   │   │       ├── monitor.py    # Monitoramento
│   │   │       └── processo.py   # Analise multi-agentes (11 endpoints)
│   │   ├── agents/               # Sistema multi-agentes
│   │   │   ├── canonical_model.py # Modelo canonico (50+ campos)
│   │   │   ├── orchestrator.py   # Orquestrador com dependencias
│   │   │   ├── specialized.py    # 14 agentes especializados
│   │   │   ├── ml_agents.py      # Agentes ML (opcional)
│   │   │   ├── pipeline_service.py # Facade + cache + tracker
│   │   │   └── captacao_service.py # Service de captacao
│   │   ├── sources/              # Fontes de dados (7 fontes)
│   │   │   ├── base.py           # BaseSource + retry/backoff
│   │   │   ├── datajud.py        # DataJud API (CNJ)
│   │   │   ├── djen_source.py    # DJEN API (CNJ)
│   │   │   ├── tjsp_dje.py       # DJe TJSP
│   │   │   ├── dejt.py           # DEJT
│   │   │   ├── querido_diario.py # Querido Diario
│   │   │   └── jusbrasil.py      # JusBrasil
│   │   ├── tests/                # Testes automatizados
│   │   ├── settings.py           # Configuracoes centralizadas
│   │   ├── route_manager.py      # Roteamento VPN/Proxy
│   │   ├── legal_parser.py       # Parser juridico
│   │   └── notifier.py           # Notificacoes WhatsApp/Email
│   ├── requirements.txt          # Dependencias Python
│   └── requirements-dev.txt      # Dependencias de desenvolvimento
├── frontend/                     # Dashboard Next.js 15
│   ├── src/
│   │   ├── app/                  # Paginas (Dashboard, Processos, Busca, Monitor)
│   │   ├── components/           # Componentes reutilizaveis
│   │   └── lib/                  # API client + auth context
│   ├── e2e/                      # Testes E2E (Playwright)
│   └── package.json
├── scripts/                      # Scripts de setup
├── docker-compose.yml            # Orquestracao Docker
├── Dockerfile.backend            # Imagem do backend
├── Dockerfile.frontend           # Imagem do frontend
├── Makefile                      # Comandos uteis
├── .env.example                  # Template de variaveis de ambiente
└── .gitignore
```

## Endpoints Principais

### Autenticacao
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login (retorna JWT) |
| GET | `/api/auth/me` | Dados do usuario |
| POST | `/api/auth/refresh` | Renovar token |

### Processo (Analise Multi-Agentes)
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/processo/analisar` | Analise completa com pipeline |
| GET | `/api/processo/{numero}` | Processo enriquecido |
| GET | `/api/processo/{numero}/resumo` | Visao executiva |
| GET | `/api/processo/{numero}/timeline` | Timeline interativa |
| GET | `/api/processo/{numero}/riscos` | Indicadores de risco |
| WS | `/api/processo/ws/{numero}` | Progresso em tempo real |

### Captacao Automatizada
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/captacao/criar` | Criar captacao |
| GET | `/api/captacao/listar` | Listar captacoes |
| POST | `/api/captacao/{id}/executar` | Executar sob demanda |
| GET | `/api/captacao/{id}/historico` | Historico de execucoes |
| GET | `/api/captacao/{id}/diff` | Comparar execucoes |

### Busca
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/datajud/buscar` | Busca no DataJud |
| POST | `/api/djen/buscar` | Busca no DJEN |
| POST | `/api/buscar/unificada` | Busca unificada |

### Monitor
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/monitor/add` | Adicionar monitorado |
| GET | `/api/monitor/list` | Listar monitorados |
| GET | `/api/monitor/stats` | Estatisticas |

## Configuracao de Proxy (DJEN)

A API DJEN do CNJ requer IP brasileiro. Para acessar de fora do Brasil:

1. Configure um proxy residencial brasileiro (ex: Bright Data)
2. Preencha as variaveis `BRIGHT_DATA_*` no `.env`
3. O sistema usara automaticamente o proxy para requisicoes ao DJEN

## Licenca

Proprietario - Todos os direitos reservados.
