# Documento Tecnico — Captacao Peticao Blindada

> Versao: 1.2.0 | Atualizado: 2026-04-18 | Para: Desenvolvedores e DevOps

---

## 1. Visao Geral da Arquitetura

```
                        Internet
                           |
                captacao.jurislaw.com.br
                           |
                [Contabo 207.180.199.121]
                           |
                  [Nginx Reverse Proxy]
                    /              \
                   /                \
        :3001 (frontend)     :8001 (backend)
         Next.js 15.1.0       FastAPI + Uvicorn
         React 19.0.0         Python 3.12
         Tailwind CSS 3.4     SQLite WAL
         Axios                APScheduler
                              14 Agentes IA
                                   |
                 +--------+--------+--------+--------+
                 |        |        |        |        |
             DataJud    DJEN    TJSP DJe   DEJT   JusBrasil
             (CNJ)     (CNJ)   (scrape)  (scrape) (Bright Data)
                         |
                   Bright Data
                 Residential Proxy
                   (IPs Brasil)
```

### Stack Tecnologico

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Frontend | Next.js + React + TypeScript | 15.1.0 / 19.0.0 / 5.7 |
| UI | Tailwind CSS + Radix UI + Lucide React | 3.4 / latest / 0.468 |
| HTTP Client | Axios | 1.7.9 |
| Backend | FastAPI + Uvicorn + Pydantic | >=0.104 / >=0.24 / >=2.5 |
| Auth | python-jose (JWT) + passlib (bcrypt) | HS256, 60min expiry |
| Database | SQLite + WAL mode | Built-in Python |
| Scheduler | APScheduler | >=3.10 |
| Web Scraping | BeautifulSoup4 + lxml | HTML parsing |
| PDF | pdfplumber | PDF extraction |
| Proxy | Bright Data Residential (BR) | brd.superproxy.io:33335 |
| Containers | Docker + Docker Compose | v3.8 |
| Reverse Proxy | Nginx | Em producao |
| Testes | Pytest (backend) + Playwright (frontend E2E) | >=8.0 / latest |

---

## 2. Estrutura de Diretorios

```
captacao-blindada/
├── backend/
│   ├── requirements.txt              # Dependencias Python
│   ├── requirements-dev.txt          # Dependencias dev (pytest, ruff, mypy)
│   └── djen/
│       ├── settings.py               # Configuracao centralizada (env vars)
│       ├── route_manager.py          # Roteamento de proxy por fonte
│       ├── legal_parser.py           # Extracao de entidades via regex
│       ├── notifier.py               # Notificacoes WhatsApp + Email
│       ├── api/
│       │   ├── app.py                # FastAPI app, lifespan, scheduler, entrypoint
│       │   ├── auth.py               # JWT auth, user store, endpoints
│       │   ├── database.py           # SQLite CRUD (7 tabelas, 630 linhas)
│       │   ├── schemas.py            # 30+ modelos Pydantic + enums
│       │   ├── resultado_repository.py # Repositorio de resultados de analise
│       │   └── routers/
│       │       ├── captacao.py       # 14 endpoints + WebSocket
│       │       ├── datajud.py        # 4 endpoints
│       │       ├── djen_router.py    # 7 endpoints
│       │       ├── health.py         # 1 endpoint
│       │       ├── monitor.py        # 7 endpoints
│       │       └── processo.py       # 14 endpoints + WebSocket
│       ├── sources/
│       │   ├── base.py               # BaseSource ABC + PublicacaoResult dataclass
│       │   ├── datajud.py            # DataJud API (60+ tribunais)
│       │   ├── djen_source.py        # DJEN API (proxy BR obrigatorio)
│       │   ├── tjsp_dje.py           # TJSP DJe web scraper (JSF)
│       │   ├── dejt.py               # DEJT web scraper (JSF)
│       │   ├── querido_diario.py     # Querido Diario REST API
│       │   └── jusbrasil.py          # JusBrasil via Bright Data Web Unlocker
│       ├── agents/
│       │   ├── canonical_model.py    # ProcessoCanonical (modelo central, 50+ campos)
│       │   ├── orchestrator.py       # Registro e orquestracao de agentes
│       │   ├── specialized.py        # 14 agentes heuristicos em 6 camadas
│       │   ├── ml_agents.py          # 4 agentes LLM com fallback
│       │   ├── pipeline_service.py   # Pipeline facade, cache L1, tracker
│       │   └── captacao_service.py   # Servico de captacao automatizada
│       ├── config/
│       │   └── tribunais_dje.json    # Mapeamento de 60+ tribunais
│       ├── tests/                    # 9 arquivos de testes
│       └── scripts/                  # 6 scripts utilitarios
├── frontend/
│   ├── package.json                  # Dependencias Node.js
│   ├── next.config.ts                # Proxy /api -> localhost:8000
│   ├── tailwind.config.ts            # Tema legal/gold/risco
│   ├── tsconfig.json                 # TypeScript strict mode
│   ├── playwright.config.ts          # E2E testing config
│   ├── e2e/                          # 8 arquivos de testes E2E
│   └── src/
│       ├── app/
│       │   ├── globals.css           # CSS vars (light/dark theme)
│       │   ├── layout.tsx            # Root server layout
│       │   ├── client-layout.tsx     # Auth guard + Sidebar wrapper
│       │   ├── page.tsx              # Dashboard (/)
│       │   ├── login/page.tsx        # Login (/login)
│       │   ├── processo/page.tsx     # Analise de processos (/processo)
│       │   ├── processo/[numero]/page.tsx  # Detalhe de processo
│       │   ├── busca/page.tsx        # Busca unificada (/busca)
│       │   ├── monitor/page.tsx      # Monitor (/monitor)
│       │   └── captacao/page.tsx     # Captacao automatizada (/captacao)
│       ├── components/
│       │   ├── Sidebar.tsx           # Menu lateral colapsavel
│       │   ├── LoadingSpinner.tsx     # Spinner de carregamento
│       │   ├── ProcessoCard.tsx      # Card de processo
│       │   ├── RiskBadge.tsx         # Badge + Gauge de risco
│       │   ├── StatsCard.tsx         # Card de estatisticas
│       │   └── TimelineView.tsx      # Visualizacao de timeline
│       └── lib/
│           ├── api.ts                # ApiClient singleton (30+ metodos)
│           ├── auth-context.tsx      # React Context de autenticacao
│           └── utils.ts              # Utilitario cn() (tailwind-merge)
├── docker-compose.yml                # Orquestracao de containers
├── Dockerfile.backend                # Build do backend
├── Dockerfile.frontend               # Build do frontend
├── Dockerfile                        # Build all-in-one (alternativo)
├── Makefile                          # Comandos dev/test/build/deploy
├── pyproject.toml                    # Config pytest/ruff/mypy
├── .env.example                      # Template de variaveis de ambiente
├── scripts/
│   ├── setup.sh                      # Setup Linux/macOS
│   └── setup.ps1                     # Setup Windows
└── docs/                             # Documentacao
```

---

## 3. Banco de Dados (SQLite)

### 3.1 Tabelas

O sistema usa SQLite com 7 tabelas. Arquivo em producao: `/app/data/captacao_blindada.db` (Docker volume `captacao-data`).

#### `monitorados` — Itens monitorados (OAB, processo, advogado, parte)
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| tipo | TEXT | NOT NULL | processo, oab, advogado, parte |
| valor | TEXT | NOT NULL | Valor de busca (ex: "12345/SP") |
| nome_amigavel | TEXT | — | Nome amigavel |
| ativo | BOOLEAN | DEFAULT 1 | Ativo/inativo |
| tribunal | TEXT | — | Filtro de tribunal |
| fontes | TEXT | — | Fontes (separadas por virgula) |
| criado_em | TIMESTAMP | DEFAULT NOW | Criacao |
| atualizado_em | TIMESTAMP | DEFAULT NOW | Atualizacao |
| ultima_busca | TIMESTAMP | — | Ultima busca executada |

#### `publicacoes` — Publicacoes judiciais encontradas
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| hash | TEXT | UNIQUE | Hash SHA-256 para deduplicacao |
| fonte | TEXT | — | datajud, djen, tjsp_dje, dejt, etc. |
| tribunal | TEXT | — | Sigla do tribunal |
| data_publicacao | TEXT | — | Data da publicacao |
| conteudo | TEXT | — | Texto completo |
| numero_processo | TEXT | — | Numero do processo |
| classe_processual | TEXT | — | Classe processual |
| orgao_julgador | TEXT | — | Orgao julgador |
| assuntos | TEXT | — | Assuntos (JSON) |
| movimentos | TEXT | — | Movimentacoes (JSON) |
| url_origem | TEXT | — | URL da fonte original |
| caderno | TEXT | — | Caderno do diario |
| pagina | TEXT | — | Pagina |
| oab_encontradas | TEXT | — | OABs encontradas (JSON) |
| advogados | TEXT | — | Advogados (JSON) |
| partes | TEXT | — | Partes (JSON) |
| notificado | BOOLEAN | DEFAULT 0 | Se notificacao foi enviada |
| monitorado_id | INTEGER | FK → monitorados(id) | Monitor vinculado |
| captacao_id | INTEGER | — | Captacao vinculada |
| criado_em | TIMESTAMP | DEFAULT NOW | Data de insercao |

#### `buscas` — Log de buscas executadas
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| tipo | TEXT | — | Tipo de busca |
| fonte | TEXT | — | Fonte utilizada |
| tribunal | TEXT | — | Tribunal |
| termos | TEXT | — | Termos de busca |
| resultados | INTEGER | DEFAULT 0 | Quantidade de resultados |
| status | TEXT | — | sucesso / erro |
| duracao_ms | INTEGER | — | Duracao em ms |
| erro | TEXT | — | Mensagem de erro |
| criado_em | TIMESTAMP | DEFAULT NOW | Data da busca |

#### `health_checks` — Verificacoes de saude das fontes
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| source | TEXT | NOT NULL | Nome da fonte |
| status | TEXT | NOT NULL | healthy / unhealthy / degraded |
| latency_ms | REAL | — | Latencia em ms |
| message | TEXT | — | Mensagem de status |
| proxy_used | BOOLEAN | DEFAULT 0 | Se proxy foi usado |
| criado_em | TIMESTAMP | DEFAULT NOW | Data do check |

#### `captacoes` — Regras de captacao automatizada
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| nome | TEXT | NOT NULL | Nome da captacao |
| descricao | TEXT | — | Descricao |
| fonte | TEXT | NOT NULL | Fonte: datajud, djen, etc. |
| tipo_busca | TEXT | NOT NULL | processo, oab, advogado, parte, termo_livre |
| termos | TEXT | NOT NULL | Termos de busca (JSON list) |
| tribunal | TEXT | — | Filtro de tribunal |
| status | TEXT | DEFAULT 'ativa' | ativa, pausada, concluida, erro |
| intervalo_minutos | INTEGER | DEFAULT 120 | Intervalo entre execucoes |
| hora_inicio | TEXT | DEFAULT '06:00' | Horario permitido inicio |
| hora_fim | TEXT | DEFAULT '22:00' | Horario permitido fim |
| dias_semana | TEXT | DEFAULT '1,2,3,4,5' | Dias permitidos (1=Seg) |
| max_resultados | INTEGER | DEFAULT 100 | Limite de resultados |
| filtro_data_inicio | TEXT | — | Filtro data inicio |
| filtro_data_fim | TEXT | — | Filtro data fim |
| filtro_classe | TEXT | — | Filtro classe processual |
| filtro_orgao | TEXT | — | Filtro orgao julgador |
| notificar_whatsapp | BOOLEAN | DEFAULT 0 | Notificar via WhatsApp |
| notificar_email | BOOLEAN | DEFAULT 0 | Notificar via email |
| whatsapp_destino | TEXT | — | Numero WhatsApp destino |
| email_destino | TEXT | — | Email destino |
| total_execucoes | INTEGER | DEFAULT 0 | Total de execucoes |
| total_resultados | INTEGER | DEFAULT 0 | Total resultados encontrados |
| ultima_execucao | TIMESTAMP | — | Ultima execucao |
| proxima_execucao | TIMESTAMP | — | Proxima execucao agendada |
| criado_em | TIMESTAMP | DEFAULT NOW | Criacao |
| atualizado_em | TIMESTAMP | DEFAULT NOW | Atualizacao |

#### `execucoes_captacao` — Historico de execucoes de captacao
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| captacao_id | INTEGER | FK → captacoes(id) | Captacao pai |
| inicio | TIMESTAMP | — | Inicio da execucao |
| fim | TIMESTAMP | — | Fim da execucao |
| status | TEXT | — | executando, sucesso, erro |
| fonte | TEXT | — | Fonte utilizada |
| parametros_json | TEXT | — | Parametros (JSON) |
| total_resultados | INTEGER | DEFAULT 0 | Total encontrado |
| novos_resultados | INTEGER | DEFAULT 0 | Novos (nao duplicados) |
| duracao_ms | INTEGER | — | Duracao em ms |
| erro | TEXT | — | Erro se falhou |
| criado_em | TIMESTAMP | DEFAULT NOW | Criacao |

#### `resultados_analise` — Resultados de analise de processos
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| numero_processo | TEXT | UNIQUE | Numero CNJ |
| tribunal | TEXT | — | Tribunal |
| dados_json | TEXT | — | ProcessoCanonical completo (JSON) |
| resumo_executivo | TEXT | — | Resumo executivo |
| risco_geral | TEXT | — | Nivel de risco |
| risco_score | REAL | — | Score de risco (0-100) |
| status_processo | TEXT | — | Status do processo |
| fase | TEXT | — | Fase processual |
| area | TEXT | — | Area do direito |
| valor_causa | REAL | — | Valor da causa |
| total_movimentacoes | INTEGER | — | Total de movimentacoes |
| total_comunicacoes | INTEGER | — | Total de comunicacoes |
| processing_time_ms | REAL | — | Tempo de processamento |
| criado_em | TIMESTAMP | DEFAULT NOW | Criacao |
| atualizado_em | TIMESTAMP | DEFAULT NOW | Atualizacao |

---

## 4. Endpoints da API (45+)

### 4.1 Autenticacao (`/api/auth/`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/api/auth/login` | Nao | Login com username/password (form-urlencoded), retorna JWT |
| GET | `/api/auth/me` | Sim | Retorna dados do usuario autenticado |
| POST | `/api/auth/refresh` | Sim | Renova token JWT |
| POST | `/api/auth/register` | Admin | Registra novo usuario |

### 4.2 Busca Unificada (`/api/buscar/`)

| Metodo | Rota | Auth | Parametros | Descricao |
|--------|------|------|------------|-----------|
| POST | `/api/buscar/unificada` | Nao | Body: termo, tipo, fontes[], tribunal, data_inicio, data_fim, limite | Busca simultanea em DataJud + DJEN (ThreadPoolExecutor) |

### 4.3 DataJud (`/api/datajud/`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/api/datajud/buscar` | Nao | Busca no DataJud por termo, tribunal, datas |
| GET | `/api/datajud/processo/{numero}` | Nao | Busca processo especifico |
| GET | `/api/datajud/tribunais` | Nao | Lista tribunais disponiveis (60+) |
| GET | `/api/datajud/health` | Nao | Health check do DataJud |

### 4.4 DJEN (`/api/djen/`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/api/djen/buscar` | Nao | Busca no DJEN por termo |
| GET | `/api/djen/processo/{numero}` | Nao | Busca por numero de processo |
| GET | `/api/djen/oab/{numero}/{uf}` | Nao | Busca por OAB + UF |
| GET | `/api/djen/advogado/{nome}` | Nao | Busca por nome de advogado |
| GET | `/api/djen/parte/{nome}` | Nao | Busca por nome de parte |
| GET | `/api/djen/tribunais` | Nao | Lista tribunais DJEN (30+) |
| GET | `/api/djen/health` | Nao | Health check do DJEN (com proxy) |

### 4.5 Monitor (`/api/monitor/`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/api/monitor/add` | Nao | Adiciona item monitorado |
| GET | `/api/monitor/list` | Nao | Lista itens monitorados |
| GET | `/api/monitor/publicacoes/recentes` | Nao | Publicacoes recentes (paginado) |
| GET | `/api/monitor/stats` | Nao | Estatisticas de monitoramento |
| GET | `/api/monitor/{id}` | Nao | Obter monitor especifico |
| PUT | `/api/monitor/{id}` | Nao | Atualizar monitor |
| DELETE | `/api/monitor/{id}` | Nao | Deletar monitor |

### 4.6 Processo (`/api/processo/`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/api/processo/analisar` | Nao | Analise batch de processos |
| GET | `/api/processo/agents` | Nao | Lista agentes registrados |
| GET | `/api/processo/cache/stats` | Nao | Estatisticas do cache L1 |
| GET | `/api/processo/resultados` | Nao | Lista resultados armazenados (paginado) |
| GET | `/api/processo/resultados/stats` | Nao | Estatisticas dos resultados |
| GET | `/api/processo/{numero}` | Nao | Analise completa de processo (pipeline) |
| GET | `/api/processo/{numero}/resumo` | Nao | Resumo executivo |
| GET | `/api/processo/{numero}/timeline` | Nao | Timeline de movimentacoes |
| GET | `/api/processo/{numero}/riscos` | Nao | Analise de riscos |
| GET | `/api/processo/{numero}/status` | Nao | Status do processo |
| DELETE | `/api/processo/resultados/{numero}` | Nao | Deletar resultado |
| DELETE | `/api/processo/cache` | Nao | Limpar cache L1 |
| DELETE | `/api/processo/{numero}/cache` | Nao | Deletar processo do cache |
| WS | `/api/processo/ws/{numero}` | Nao | WebSocket de progresso em tempo real |

### 4.7 Captacao (`/api/captacao/`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/api/captacao/criar` | Nao | Criar captacao |
| GET | `/api/captacao/listar` | Nao | Listar captacoes (paginado) |
| GET | `/api/captacao/stats` | Nao | Estatisticas de captacao |
| POST | `/api/captacao/preview` | Nao | Preview de captacao (sem salvar) |
| POST | `/api/captacao/executar-todas` | Nao | Executar todas as captacoes pendentes |
| GET | `/api/captacao/{id}` | Nao | Obter captacao especifica |
| PUT | `/api/captacao/{id}` | Nao | Atualizar captacao |
| DELETE | `/api/captacao/{id}` | Nao | Desativar captacao |
| POST | `/api/captacao/{id}/executar` | Nao | Executar captacao agora |
| POST | `/api/captacao/{id}/pausar` | Nao | Pausar captacao |
| POST | `/api/captacao/{id}/retomar` | Nao | Retomar captacao |
| GET | `/api/captacao/{id}/historico` | Nao | Historico de execucoes |
| GET | `/api/captacao/{id}/resultados` | Nao | Resultados encontrados |
| GET | `/api/captacao/{id}/diff` | Nao | Novos desde ultima execucao |
| WS | `/api/captacao/ws/{id}` | Nao | WebSocket de progresso |

### 4.8 Health (`/api/health`)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | `/api/health` | Nao | Health check unificado (todas as fontes + DB) |

---

## 5. Sistema de Agentes (14 agentes, 6 camadas)

O pipeline de analise de processos usa 14 agentes organizados em 6 camadas que executam em paralelo respeitando dependencias.

### 5.1 Ordem de Execucao

```
Camada 1: [validador]
     ↓
Camada 2: [coletor_datajud, coletor_djen]         (paralelo)
     ↓
Camada 3: [extrator_entidades, analisador_movimentacoes]  (paralelo)
     ↓
Camada 4: [classificador_causa, extrator_valores, analisador_cronologia]  (paralelo)
     ↓
Camada 5: [calculador_prazos, analisador_risco, analisador_jurisprudencia]  (paralelo)
     ↓
Camada 6: [gerador_resumo, validador_conformidade, previsor_resultado]  (paralelo)
```

### 5.2 Descricao dos Agentes

| Agente | Camada | Descricao |
|--------|--------|-----------|
| `validador` | 1 | Valida formato CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) |
| `coletor_datajud` | 2 | Coleta dados do DataJud API |
| `coletor_djen` | 2 | Coleta comunicacoes do DJEN API |
| `extrator_entidades` | 3 | Extrai partes, advogados, OABs, CPFs, CNPJs |
| `analisador_movimentacoes` | 3 | Classifica movimentacoes por tipo |
| `classificador_causa` | 4 | Classifica area do direito e classe processual |
| `extrator_valores` | 4 | Extrai valores monetarios (R$) |
| `analisador_cronologia` | 4 | Constroi timeline, calcula duracoes |
| `calculador_prazos` | 5 | Calcula prazos processuais |
| `analisador_risco` | 5 | Scoring de risco multi-fator (0-100) |
| `analisador_jurisprudencia` | 5 | Gera referencias jurisprudenciais |
| `gerador_resumo` | 6 | Gera resumo executivo com recomendacoes |
| `validador_conformidade` | 6 | Verifica conformidade procedimental |
| `previsor_resultado` | 6 | Preve resultado provavel com confianca |

### 5.3 Agentes ML (opcionais)

Quando `USE_ML_AGENTS=true`, 4 agentes heuristicos sao substituidos por versoes LLM:

| Heuristico | ML | LLM API |
|------------|-----|---------|
| `classificador_causa` | `classificador_causa_ml` | Gameron API (gpt-4.1-mini) |
| `previsor_resultado` | `previsor_resultado_ml` | Gameron API |
| `gerador_resumo` | `gerador_resumo_ml` | Gameron API |
| `analisador_jurisprudencia` | `analisador_jurisprudencia_ml` | Gameron API |

Todos os agentes ML possuem fallback automatico para a versao heuristica se a LLM falhar.

---

## 6. Fontes de Dados (7)

| # | Fonte | Classe | Base URL | Acesso | Dados |
|---|-------|--------|----------|--------|-------|
| 1 | DataJud (CNJ) | `DataJudSource` | `api-publica.datajud.cnj.jus.br` | API Key (header) | Metadados processuais de 60+ tribunais |
| 2 | DJEN (CNJ) | `DJENSource` | `comunicaapi.pje.jus.br` | IP brasileiro (proxy) | Comunicacoes processuais do PJe |
| 3 | TJSP DJe | `TJSPDJeSource` | `dje.tjsp.jus.br` | Web scraping (JSF) | Diario eletronico do TJSP |
| 4 | DEJT | `DEJTSource` | `dejt.jt.jus.br` | Web scraping (JSF) | Diario da Justica do Trabalho |
| 5 | Querido Diario | `QueridoDiarioSource` | `api.queridodiario.ok.org.br` | API REST publica | Diarios oficiais municipais |
| 6 | JusBrasil | `JusBrasilSource` | `jusbrasil.com.br` | Bright Data Web Unlocker | Jurisprudencia e conteudo juridico |
| 7 | Gameron LLM | `LLMClient` | `api.gameron.io/v1` | API Key (Bearer) | Analise IA (classificacao, previsao) |

### Proxy e Roteamento

O `RouteManager` gerencia qual proxy usar por fonte:

| Fonte | Proxy | Motivo |
|-------|-------|--------|
| datajud | Direto (sem proxy) | API publica, aceita qualquer IP |
| djen_api | Residential Proxy (BR) | Requer IP brasileiro |
| tjsp_dje | Residential Proxy (BR) | Geo-restrito ao Brasil |
| dejt | Residential Proxy (BR) | Geo-restrito ao Brasil |
| querido_diario | Direto | API publica |
| jusbrasil | Bright Data Web Unlocker | Cloudflare anti-bot |

---

## 7. Cache e Performance

### Cache L1 (Memoria)
- Classe: `ProcessoCache` em `pipeline_service.py`
- Estrategia: LRU com TTL
- Max: 100 entradas
- TTL: 3600 segundos (1 hora)
- Eviction: Remove entrada mais antiga quando cheio

### Cache L2 (SQLite)
- Tabela: `resultados_analise`
- Persistente (Docker volume)
- UPSERT por numero_processo

### Deduplicacao de Publicacoes
- Hash SHA-256 baseado em: fonte + tribunal + processo + data + conteudo[:200]
- Coluna `hash` com constraint UNIQUE na tabela `publicacoes`

---

## 8. Scheduler (APScheduler)

O sistema de agendamento na versão 1.2 atua de forma convergente (Unificação do DataJud + DJEN):

| Job | Intervalo | Descricao |
|-----|-----------|-----------|
| `monitor_cycle` | A cada 1 hora | Busca simultânea no DataJud (movimentações) e DJEN (publicações inteiras) para todos os itens. Alimenta DB de forma consistente sem duplicidade de chamadas. |
| `processos_datajud_cycle`| A cada 6 horas | Atualiza o painel "Processos" via consultas passivas ao DataJud, capturando novas movimentações na timeline. |
| `captacao_cycle` | A cada 30 minutos | Chama `CaptacaoService.executar_todas()`, pesquisa pró-ativa de leads. |

---

## 9. Autenticacao

- **Algoritmo**: JWT HS256
- **Expiracao**: 60 minutos (configuravel via `JWT_EXPIRE_MINUTES`)
- **User Store**: In-memory (nao persistido em SQLite)
- **Roles**: admin, user, viewer
- **Admin default**: username e password vem de env vars (`ADMIN_USERNAME`, `ADMIN_PASSWORD`)
- **Token**: Armazenado no `localStorage` do frontend
- **Interceptor**: Axios injeta header `Authorization: Bearer {token}` em toda request
- **401 Handler**: Frontend remove token e redireciona para `/login`

---

## 10. Frontend — Paginas e Rotas

| Rota | Componente | Descricao |
|------|-----------|-----------|
| `/` | `DashboardPage` | Painel com 4 StatsCards, busca rapida, processos recentes |
| `/login` | `LoginPage` | Login com split-screen, branding OpenClaw |
| `/processo` | `ProcessoPage` | Analise de processos com 4 tabs (Resumo, Timeline, Riscos, Dados) |
| `/processo/[numero]` | `ProcessoDetailPage` | Detalhe de processo com partes, timeline, movimentacoes |
| `/busca` | `BuscaPage` | Busca unificada com 3 fontes (Unificada, DataJud, DJEN), filtros |
| `/monitor` | `MonitorPage` | Monitor com tabela, stats, publicacoes expansiveis |
| `/captacao` | `CaptacaoPage` | Captacao automatizada com dashboard, cards, formulario de criacao |

### Componentes Compartilhados

| Componente | Props | Descricao |
|-----------|-------|-----------|
| `Sidebar` | — | Menu colapsavel, 5 links, dark mode, logout |
| `LoadingSpinner` | size, text | Spinner com 3 tamanhos |
| `StatsCard` | title, value, icon, description, trend | Card de estatisticas |
| `ProcessoCard` | processo | Card com numero, classe, tribunal, risco |
| `RiskBadge` | level, score | Badge colorido por nivel de risco |
| `RiskGauge` | level, score | Gauge SVG semi-circular |
| `TimelineView` | events | Timeline vertical com icones por tipo |

### API Client (`api.ts`)

Singleton `ApiClient` com Axios. 30+ metodos mapeando todos os endpoints do backend. Interceptors para JWT e 401.

---

## 11. Variaveis de Ambiente

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `CAPTACAO_PORT` | 8000 | Porta do backend |
| `CAPTACAO_HOST` | 0.0.0.0 | Host do backend |
| `CAPTACAO_DB_PATH` | data/captacao_blindada.db | Caminho do SQLite |
| `JWT_SECRET_KEY` | dev-secret... | Chave de assinatura JWT |
| `JWT_EXPIRE_MINUTES` | 60 | Expiracao do token |
| `ADMIN_USERNAME` | admin | Usuario admin |
| `ADMIN_PASSWORD` | admin | Senha admin |
| `ADMIN_FULL_NAME` | Administrador | Nome do admin |
| `DATAJUD_API_KEY` | cDZHYz... | API Key do DataJud |
| `DATAJUD_BASE_URL` | https://api-publica.datajud.cnj.jus.br | URL base DataJud |
| `DJEN_API_BASE_URL` | https://comunicaapi.pje.jus.br | URL base DJEN |
| `BRIGHT_DATA_CUSTOMER_ID` | — | ID cliente Bright Data |
| `BRIGHT_DATA_PROXY_HOST` | brd.superproxy.io | Host do proxy |
| `BRIGHT_DATA_PROXY_PORT` | 33335 | Porta do proxy |
| `BRIGHT_DATA_PROXY_USERNAME` | — | Usuario do proxy |
| `BRIGHT_DATA_PROXY_PASSWORD` | — | Senha do proxy |
| `BRIGHT_DATA_API_KEY` | — | API Key Web Unlocker |
| `USE_ML_AGENTS` | false | Ativar agentes LLM |
| `LLM_API_URL` | https://api.gameron.io/v1/... | URL da API LLM |
| `LLM_API_KEY` | — | Chave da API LLM |
| `LLM_MODEL` | gpt-4.1-mini | Modelo LLM |
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | URL do backend para o frontend |

---

## 12. Deploy em Producao

### Servidor
- **Provider**: Contabo VPS
- **IP**: 207.180.199.121
- **OS**: Linux
- **Dominio**: captacao.jurislaw.com.br (SSL via Nginx)

### Processo de Deploy

```bash
# 1. Editar arquivos localmente

# 2. SCP para o servidor
scp -i ~/.ssh/contabo_key arquivo root@207.180.199.121:/opt/captacao-blindada/caminho/

# 3. Rebuild e restart dos containers
ssh root@207.180.199.121 "cd /opt/captacao-blindada && docker compose up --build -d"

# 4. Verificar logs
ssh root@207.180.199.121 "docker compose logs --tail=50 backend"
ssh root@207.180.199.121 "docker compose logs --tail=50 frontend"

# 5. Testar
curl -s https://captacao.jurislaw.com.br/api/health
curl -s -o /dev/null -w '%{http_code}' https://captacao.jurislaw.com.br/
```

### Docker Compose (producao)

- `backend` → container `captacao-backend`, porta 8001:8000
- `frontend` → container `captacao-frontend`, porta 3001:3000
- Volume `captacao-data` → `/app/data/` (persiste SQLite)
- `.env` com credenciais de producao

### Nginx

- Reverse proxy em `/etc/nginx/sites-enabled/`
- `captacao.jurislaw.com.br` → frontend (:3001) + `/api/*` → backend (:8001)
- `proxy_read_timeout 300s` (configurado para buscas lentas)
- SSL configurado

---

## 13. Testes

### Backend (Pytest)
```bash
cd backend && pytest djen/tests/ -v --tb=short
```
- 9 arquivos de teste cobrindo auth, endpoints, database, schemas, pipeline

### Frontend (Playwright E2E)
```bash
cd frontend && npx playwright test
```
- 8 specs: auth, dashboard, busca, processo, monitor, responsive, accessibility

### Linting
```bash
ruff check backend/djen/    # Python
cd frontend && npm run lint  # TypeScript/ESLint
```

---

## 14. Makefile (Comandos Rapidos)

| Comando | Descricao |
|---------|-----------|
| `make install` | Instala deps backend |
| `make dev` | Inicia backend dev (uvicorn --reload) |
| `make test` | Roda testes backend |
| `make lint` | Linting com ruff |
| `make frontend-dev` | Inicia frontend dev |
| `make docker-build` | Build dos containers |
| `make docker-up` | Sobe containers |
| `make docker-down` | Para containers |
| `make docker-logs` | Logs em tempo real |
| `make setup` | Setup completo (backend + frontend) |

---

## 15. Problemas Conhecidos e Solucoes

| Problema | Causa | Solucao |
|----------|-------|---------|
| DJEN retorna 403 | Servidor Contabo tem IP alemao | Proxy residencial BR via Bright Data (route_manager.py) |
| Busca lenta (>60s) | DataJud timeout por tribunal | nginx proxy_read_timeout=300s, executor timeout=180s |
| Login falha com admin/admin | .env producao tem senha diferente | Usar credenciais do .env (ADMIN_PASSWORD) |
| Build frontend falha | Erros TypeScript | Verificar types no api.ts vs componentes |
| DJEN health "unhealthy" | Proxy nao configurado | Verificar BRIGHT_DATA_* no .env |
