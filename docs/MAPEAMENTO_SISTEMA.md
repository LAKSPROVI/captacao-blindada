# Mapeamento do Sistema — Captacao Peticao Blindada

> Versao: 3.0.0 (Security Hardening) | Atualizado: 2026-04-26 | Para: Equipe tecnica e gestao | 250+ implementações | 120+ endpoints

---

## 1. Visao Geral

```
                          INTERNET
                             |
                  captacao.jurislaw.com.br
                       (DNS A Record)
                             |
                  ┌──────────────────────┐
                   │  Contabo VPS           │
                   │  207.180.199.121       │
                   │  Ubuntu / Docker       │
                   │                        │
                   │  ┌──────────────────┐  │
                   │  │ Caddy (Rev Proxy)│  │
                   │  │ :80 → :443 auto │  │
                   │  │ TLS + Headers    │  │
                   │  └────────┬─────────┘  │
                   │           │            │
                   │     ┌─────┴─────┐      │
                   │     │          │      │
                   │  ┌──┴───┐ ┌───┴──┐   │
                   │  │ FE   │ │ BE   │   │
                   │  │:3000 │ │:8000 │   │
                   │  │intern│ │intern│   │
                   │  └──────┘ └──┬───┘   │
                   │              │       │
                   │       ┌──────┴──┐    │
                   │       │ SQLite  │    │
                   │       │ (vol)   │    │
                   │       └─────────┘    │
                   └────────────────────────┘
                             │
               ┌─────────────┼─────────────┐
               │             │             │
          ┌────┴────┐  ┌────┴────┐  ┌────┴────┐
          │ DataJud │  │  DJEN   │  │ Bright  │
          │  (CNJ)  │  │  (CNJ)  │  │  Data   │
           │ API Key │  │ via BR  │  │  Proxy  │
           │(encrypt)│  │verify=T │  │(encrypt)│
           └─────────┘  └─────────┘  └─────────┘

> Portas externas: 80 (HTTP redirect) e 443 (HTTPS) via Caddy.
> Portas internas (3000, 8000) NAO expostas ao host — apenas via rede Docker interna.
> API keys criptografadas em repouso via Fernet (crypto.py).
> DJEN com verify=True para validacao SSL.
```

---

## 2. Componentes do Sistema

### 2.1 Frontend (Next.js)

| Atributo | Valor |
|----------|-------|
| Framework | Next.js 15.1.0 + React 19 + TypeScript 5.7 |
| UI | Tailwind CSS 3.4 + Radix UI + Lucide Icons |
| HTTP Client | Axios 1.7.9 (ApiClient singleton) |
| Container | Node 20 Alpine, porta interna 3000 (NAO exposta) |
| Build mode | Standalone (next build → standalone output) |
| Autenticacao | httpOnly cookies (NAO usa localStorage para tokens) |
| Security Headers | CSP, HSTS, X-Frame-Options, X-Content-Type-Options |

#### Paginas (15 rotas)

| Rota | Arquivo | Funcao |
|------|---------|--------|
| `/` | `app/page.tsx` | Dashboard — visao geral, stats, processos recentes |
| `/login` | `app/login/page.tsx` | Autenticacao com usuario/senha (httpOnly cookie) |
| `/processo` | `app/processo/page.tsx` | Analise de processos com IA |
| `/processo/[numero]` | `app/processo/[numero]/page.tsx` | Detalhe de processo especifico |
| `/busca` | `app/busca/page.tsx` | Busca unificada em multiplas fontes |
| `/monitor` | `app/monitor/page.tsx` | Monitoramento de processos/OABs |
| `/captacao` | `app/captacao/page.tsx` | Captacao automatizada de publicacoes |
| `/captacao?filter=novos` | `app/captacao/page.tsx` | Auto-expande captação com novos resultados |
| `/processo?filter=recente` | `app/processo/page.tsx` | Filtra processos com movimentações recentes |
| `/processo?q={termo}` | `app/processo/page.tsx` | Busca direta por processo |
| `/configuracao-ia` | `app/configuracao-ia/page.tsx` | Configuração de modelos IA |
| `/admin/usuarios` | `app/admin/usuarios/page.tsx` | Gestão de usuários |
| `/admin/auditoria` | `app/admin/auditoria/page.tsx` | Cadeia de custódia |
| `/admin/tarifacao` | `app/admin/tarifacao/page.tsx` | Tarifação do sistema |
| `/admin/erros` | `app/admin/erros/page.tsx` | Erros do sistema |

#### Componentes (16)

| Componente | Arquivo | Funcao |
|------------|---------|--------|
| `Sidebar` | `components/Sidebar.tsx` | Menu lateral colapsavel + dark mode + logout |
| `LoadingSpinner` | `components/LoadingSpinner.tsx` | Spinner animado com texto (sm/default/lg) |
| `ProcessoCard` | `components/ProcessoCard.tsx` | Card de processo com resumo |
| `RiskBadge` + `RiskGauge` | `components/RiskBadge.tsx` | Badge e gauge visual de risco (0-100) |
| `StatsCard` | `components/StatsCard.tsx` | Card de estatistica com icone e tendencia |
| `TimelineView` | `components/TimelineView.tsx` | Linha do tempo de movimentacoes |
| `Breadcrumbs` | `components/Breadcrumbs.tsx` | Navegação breadcrumb |
| `Toast` | `components/Toast.tsx` | Notificações visuais (success/error/warning/info) |
| `Skeleton` | `components/Skeleton.tsx` | Loading states (text/card/table/circle) |
| `Modal` | `components/Modal.tsx` | Modais e confirmações |
| `CompactTable` | `components/CompactTable.tsx` | Tabela compacta reutilizável |
| `Tooltip` | `components/Tooltip.tsx` | Tooltip informativo |
| `EmptyState` | `components/EmptyState.tsx` | Estado vazio com ação |
| `OnlineIndicator` | `components/OnlineIndicator.tsx` | Indicador de status online |
| `KeyboardShortcutsHelp` | `components/KeyboardShortcutsHelp.tsx` | Ajuda de atalhos |

#### Bibliotecas (lib/)

| Arquivo | Funcao |
|---------|--------|
| `api.ts` | ApiClient singleton com 50+ metodos e 30+ interfaces |
| `auth-context.tsx` | React Context para autenticacao (login, logout, user, token) |
| `utils.ts` | Utilitario `cn()` (clsx + tailwind-merge) |

#### Hooks (4)

| Hook | Arquivo | Funcao |
|------|---------|--------|
| `useOnlineStatus` | `hooks/useOnlineStatus.ts` | Detecta status online/offline |
| `useLocalStorage` | `hooks/useLocalStorage.ts` | State persistido em localStorage |
| `useKeyboardShortcuts` | `hooks/useKeyboardShortcuts.ts` | Atalhos de teclado |
| `useDebounce` | `hooks/useDebounce.ts` | Debounce de valores |

---

### 2.2 Backend (FastAPI)

| Atributo | Valor |
|----------|-------|
| Framework | FastAPI + Uvicorn + Pydantic v2 |
| Linguagem | Python 3.11+ |
| Container | python:3.11-slim-bookworm, porta interna 8000 (NAO exposta), user non-root |
| Auth | PyJWT (HS256) + httpOnly cookies + bcrypt |
| Encryption | Fernet (AES) para API keys em repouso (crypto.py) |
| Sanitizacao | Prevencao de prompt injection (sanitize.py) |
| Banco | SQLite com WAL mode + isolamento multi-tenant |
| Scheduler | APScheduler (3 jobs: Monitor DJEN 10min, DataJud 6h, Captação 30min) |
| Rate Limiting | slowapi (GET 60/min, POST 30/min, exports 5/min) |

#### Endpoints (120+ total, 37+ routers — TODOS com autenticacao)

| Router | Prefixo | Endpoints | Funcao |
|--------|---------|-----------|--------|
| `captacao.py` | `/api/captacao` | 14 + WS | CRUD + execucao de captacoes automatizadas |
| `processo.py` | `/api/processo` | 14 + WS | Analise, resumo, timeline, riscos, comparacao |
| `monitor.py` | `/api/monitor` | 7 | CRUD de monitorados + publicacoes + stats |
| `djen_router.py` | `/api/djen` | 7 | Busca DJEN, publicacoes, tribunais |
| `datajud.py` | `/api/datajud` | 4 | Busca DataJud, detalhes de processo |
| `health.py` | `/api/health` | 1 | Health check (unico sem auth) |
| `auth.py` | `/api/auth` | 4 | Login, me, refresh, logout (httpOnly cookie) |
| `validation.py` | `/api/validation` | 5 | Validacao CNJ, OAB, tribunais |
| `webhook.py` | `/api/webhooks` | 5 | CRUD + trigger de webhooks |
| `metrics.py` | `/api/metrics` | 4 | Metricas JSON, Prometheus, health |
| `admin/*.py` | `/api/admin/*` | 20+ | Usuarios, auditoria, tarifacao, tenants, erros |
| `ia_config.py` | `/api/ia-config` | 5+ | Configuracao de modelos IA (keys criptografadas) |

> Todos os endpoints (exceto /health) exigem `Depends(get_current_user)` e filtram por `tenant_id`.

#### Detalhamento de Endpoints por Router

##### Router: Captacao (`/api/captacao`)

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/` | Listar captacoes |
| POST | `/` | Criar nova captacao |
| GET | `/stats` | Estatisticas agregadas |
| GET | `/{id}` | Detalhe de captacao |
| PUT | `/{id}` | Atualizar captacao |
| DELETE | `/{id}` | Excluir captacao |
| POST | `/{id}/executar` | Executar manualmente |
| POST | `/{id}/pausar` | Pausar captacao |
| POST | `/{id}/retomar` | Retomar captacao ativa |
| GET | `/{id}/historico` | Historico de execucoes |
| GET | `/{id}/resultados` | Resultados encontrados |
| WS | `/{id}/ws` | WebSocket de progresso em tempo real |
| GET | `/proximas` | Proximas execucoes agendadas |
| POST | `/executar-todas` | Executar todas as captacoes ativas |

##### Router: Processo (`/api/processo`)

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| POST | `/analisar` | Analisar processo via pipeline IA |
| GET | `/{numero}` | Buscar processo por numero |
| GET | `/{numero}/resumo` | Resumo gerado pela IA |
| GET | `/{numero}/timeline` | Timeline de movimentacoes |
| GET | `/{numero}/riscos` | Analise de riscos (score 0-100) |
| GET | `/{numero}/partes` | Partes do processo |
| GET | `/{numero}/documentos` | Documentos do processo |
| POST | `/comparar` | Comparar dois processos |
| GET | `/resultados` | Listar resultados armazenados |
| GET | `/resultados/{id}` | Detalhe de resultado |
| DELETE | `/resultados/{id}` | Excluir resultado |
| WS | `/ws/{numero}` | WebSocket de progresso da analise |
| POST | `/busca-unificada` | Busca em todas as fontes |
| GET | `/stats` | Estatisticas de processos |

##### Router: Monitor (`/api/monitor`)

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/` | Listar monitorados |
| POST | `/` | Criar monitorado |
| PUT | `/{id}` | Atualizar monitorado |
| DELETE | `/{id}` | Excluir monitorado |
| POST | `/{id}/toggle` | Ativar/desativar |
| GET | `/publicacoes` | Publicacoes recentes |
| GET | `/stats` | Estatisticas do monitor |

##### Router: DJEN (`/api/djen`)

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| POST | `/buscar` | Busca no DJEN |
| GET | `/publicacoes` | Publicacoes DJEN |
| GET | `/tribunais` | Lista de tribunais disponiveis |
| GET | `/publicacao/{id}` | Detalhe de publicacao |
| POST | `/buscar-oab` | Busca por OAB no DJEN |
| POST | `/buscar-parte` | Busca por nome de parte |
| GET | `/stats` | Estatisticas DJEN |

##### Router: DataJud (`/api/datajud`)

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| POST | `/buscar` | Busca no DataJud |
| GET | `/processo/{numero}` | Detalhe via DataJud |
| GET | `/tribunais` | Tribunais disponiveis |
| GET | `/stats` | Estatisticas DataJud |

##### Router: Health (`/api/health`)

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| GET | `/` | Status do sistema + fontes |

---

### 2.3 Banco de Dados (SQLite — 8 tabelas)

O banco de dados é gerenciado via **Singleton Pattern** em `database.py`.
A inicialização de tabelas e do administrador padrão ocorre no evento `lifespan` do FastAPI.

```
┌─────────────────┐     ┌──────────────────────┐
│  monitorados    │     │     publicacoes       │
│─────────────────│     │──────────────────────│
│ id (PK)         │◄───┤ monitorado_id (FK)   │
│ tipo            │     │ captacao_id           │──┐
│ valor           │     │ id (PK)              │  │
│ nome_amigavel   │     │ hash (UNIQUE)        │  │
│ ativo           │     │ fonte                │  │
│ tribunal        │     │ tribunal             │  │
│ fontes          │     │ data_publicacao      │  │
│ criado_em       │     │ conteudo             │  │
│ atualizado_em   │     │ numero_processo      │  │
│ ultima_busca    │     │ classe_processual    │  │
└─────────────────┘     │ orgao_julgador       │  │
                        │ assuntos (JSON)      │  │
                        │ movimentos (JSON)    │  │
                        │ oab_encontradas      │  │
                        │ advogados (JSON)     │  │
                        │ partes (JSON)        │  │
                        │ notificado           │  │
                        │ criado_em            │  │
                        └──────────────────────┘  │
                                                   │
┌─────────────────┐     ┌──────────────────────┐  │
│   captacoes     │     │ execucoes_captacao   │  │
│─────────────────│     │──────────────────────│  │
│ id (PK)         │◄──┐│ id (PK)              │  │
│ nome            │   ││ captacao_id (FK)     │◄─┘
│ descricao       │   │└──────────────────────┘
│ fonte           │   │
│ tipo_busca      │   │  ┌──────────────────────┐
│ termos (JSON)   │   │  │   resultados_analise │
│ tribunal        │   │  │──────────────────────│
│ status          │   │  │ id (PK)              │
│ intervalo_min   │   │  │ numero_processo      │
│ hora_inicio     │   │  │ dados (JSON)         │
│ hora_fim        │   │  │ score_risco          │
│ dias_semana     │   │  │ resumo               │
│ max_resultados  │   │  │ criado_em            │
│ filtros...      │   │  └──────────────────────┘
│ notificacoes... │   │
│ contadores...   │   │  ┌──────────────────────┐
│ criado_em       │   │  │      buscas          │
│ atualizado_em   │   │  │──────────────────────│
└─────────────────┘   │  │ id (PK)              │
                      │  │ tipo                 │
                      │  │ fonte                │
                      │  │ tribunal             │
                      │  │ termos               │
                      │  │ resultados           │
                      │  │ status               │
                      │  │ duracao_ms           │
                      │  │ erro                 │
                      │  │ criado_em            │
                      │  └──────────────────────┘
                      │
                      │  ┌──────────────────────┐
                      │  │   health_checks      │
                      │  │──────────────────────│
                      │  │ id (PK)              │
                      │  │ source               │
                      │  │ status               │
                      │  │ latency_ms           │
                      │  │ message              │
                      │  │ proxy_used           │
                      │  │ criado_em            │
                      │  └──────────────────────┘
                      │
                      └── (captacao_id referenciado
                           em publicacoes e
                           execucoes_captacao)
```

#### `processos_monitorados` — Processos monitorados para verificação automática
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| numero_processo | TEXT | UNIQUE NOT NULL | Numero CNJ |
| tribunal | TEXT | — | Tribunal |
| classe_processual | TEXT | — | Classe processual |
| orgao_julgador | TEXT | — | Orgao julgador |
| assuntos | TEXT | — | Assuntos (JSON) |
| status | TEXT | DEFAULT 'ativo' | ativo/inativo |
| origem | TEXT | DEFAULT 'monitor' | Origem do registro |
| origem_id | INTEGER | — | ID da origem |
| ultima_verificacao | TEXT | — | Ultima verificação DataJud |
| total_movimentacoes | INTEGER | DEFAULT 0 | Total de movimentações |
| movimentacoes | TEXT | — | Movimentações (JSON blob) |
| data_ultima_movimentacao | TEXT | — | Data da última movimentação |
| criado_em | TIMESTAMP | DEFAULT NOW | Criação |
| atualizado_em | TIMESTAMP | DEFAULT NOW | Atualização |

#### `processos_monitorados_historico` — Histórico de verificações
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| numero_processo | TEXT | FK | Numero do processo |
| data_verificacao | TIMESTAMP | DEFAULT NOW | Data da verificação |
| status | TEXT | — | ok/erro/sem_mudancas |
| fonte | TEXT | — | datajud/djen |
| detalhes | TEXT | — | Detalhes (JSON) |
| total_movimentacoes | INTEGER | — | Total de movimentações |
| novas_movimentacoes | INTEGER | DEFAULT 0 | Novas movimentações detectadas |

#### `processo_anotacoes` — Anotações em processos
| Coluna | Tipo | Restricao | Descricao |
|--------|------|-----------|-----------|
| id | INTEGER | PK AUTOINCREMENT | ID unico |
| numero_processo | TEXT | NOT NULL | Numero do processo |
| texto | TEXT | NOT NULL | Texto da anotação |
| tipo | TEXT | DEFAULT 'nota' | Tipo da anotação |
| criado_em | TIMESTAMP | DEFAULT NOW | Criação |

---

### 2.4 Agentes de Inteligencia Artificial (14 total)

O sistema possui um pipeline de analise composto por agentes em **6 camadas**, orquestrados pelo `orchestrator.py`.

```
Input: Numero do Processo
         │
         ▼
┌────────────────────────┐
│  CAMADA 1: Extracao    │
│  ┌──────────────────┐  │
│  │ ExtratorEntidades│  │   Regex: processos, OABs, CPFs,
│  └──────────────────┘  │   CNPJs, valores monetarios
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  CAMADA 2: Coleta      │
│  ┌──────────────────┐  │
│  │ ColetorProcessual│  │   Busca DataJud + DJEN + TJSP +
│  └──────────────────┘  │   DEJT + JusBrasil
│  ┌──────────────────┐  │
│  │ ColetorMovimentos│  │   Coleta movimentacoes processuais
│  └──────────────────┘  │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  CAMADA 3: Classificacao│
│  ┌──────────────────┐  │
│  │ ClassificadorRamo│  │   Civil, Criminal, Trabalhista,
│  └──────────────────┘  │   Tributario, etc.
│  ┌──────────────────┐  │
│  │ ClassificadorFase│  │   Conhecimento, Recursal,
│  └──────────────────┘  │   Execucao, Arquivado
│  ┌──────────────────┐  │
│  │ ClassificadorPrio│  │   Urgente, Normal, Baixa
│  └──────────────────┘  │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  CAMADA 4: Analise     │
│  ┌──────────────────┐  │
│  │ AnalisadorRisco  │  │   Score 0-100 + fatores de risco
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ AnalisadorValor  │  │   Valor da causa, honorarios,
│  └──────────────────┘  │   custas
│  ┌──────────────────┐  │
│  │ AnalisadorPrazos │  │   Prazos ativos + vencidos
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ AnalisadorPartes │  │   Polos ativo/passivo, advogados
│  └──────────────────┘  │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  CAMADA 5: Enriquecim. │
│  ┌──────────────────┐  │
│  │ Enriquecedor     │  │   Consolida dados de todas as
│  └──────────────────┘  │   fontes no modelo canonico
│  ┌──────────────────┐  │
│  │ GeradorResumo    │  │   Gera resumo em linguagem
│  └──────────────────┘  │   natural
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  CAMADA 6: ML (opc.)   │
│  ┌──────────────────┐  │
│  │ ML Classificador │  │   LLM para classificacao (fallback)
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ ML Resumo        │  │   LLM para resumo (fallback)
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ ML Risco         │  │   LLM para risco (fallback)
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ ML Predicao      │  │   LLM para predicao (fallback)
│  └──────────────────┘  │
└────────┬───────────────┘
         │
         ▼
Output: ProcessoCanonical (50+ campos)
```

#### Modelo Canonico (ProcessoCanonical)

O resultado final de toda analise e consolidado em um modelo com **50+ campos**, incluindo:

| Grupo | Campos principais |
|-------|------------------|
| Identificacao | numero, tribunal, classe, orgao_julgador, assuntos |
| Datas | distribuicao, ultimo_movimento, transito_julgado |
| Partes | polo_ativo, polo_passivo, advogados (nome, OAB) |
| Valores | valor_causa, honorarios, custas, multas |
| Classificacao | ramo_direito, fase_processual, prioridade |
| Risco | score (0-100), fatores, recomendacoes |
| Resumo | texto em linguagem natural |
| Timeline | lista de eventos com data, tipo, descricao |
| Prazos | prazos ativos, vencidos, proximos |
| Metadados | fontes consultadas, tempo de processamento, cache hit |

---

### 2.5 Fontes de Dados (7 fontes)

```
┌────────────────────────────────────────────────────────┐
│                   FONTES DE DADOS                      │
├────────────┬───────────┬──────────┬────────────────────┤
│   Fonte    │   Tipo    │  Proxy?  │    Autenticacao    │
├────────────┼───────────┼──────────┼────────────────────┤
│ DataJud    │ REST API  │   Nao    │ API Key (CNJ)      │
│ DJEN       │ REST API  │   Sim*   │ Nenhuma            │
│ TJSP DJe   │ Scraping  │   Nao    │ Nenhuma (JSF)      │
│ DEJT       │ Scraping  │   Nao    │ Nenhuma (JSF)      │
│ Querido D. │ REST API  │   Nao    │ Nenhuma            │
│ JusBrasil  │ Scraping  │   Sim    │ Bright Data Unlock |
│ Legal P.   │ Regex     │   N/A    │ N/A (local)        │
└────────────┴───────────┴──────────┴────────────────────┘

* DJEN exige IP brasileiro — proxy residencial Bright Data obrigatorio
  (servidor Contabo tem IP alemao)
```

#### Route Manager (Proxy)

O `route_manager.py` gerencia qual proxy usar para cada fonte:

```
Requisicao → RouteManager.get_route(fonte)
                    │
              ┌─────┴──────┐
              │ DEFAULT     │
              │ ROUTES      │
              ├─────────────┤
              │ djen_api →  │── residential_proxy ──→ Bright Data
              │ jusbrasil → │── web_unlocker ────────→ Bright Data
              │ datajud →   │── direct ──────────────→ Sem proxy
              │ tjsp_dje →  │── direct ──────────────→ Sem proxy
              │ dejt →      │── direct ──────────────→ Sem proxy
              └─────────────┘
```

---

### 2.6 Cache (2 niveis)

```
Requisicao de Analise
         │
         ▼
┌────────────────────┐
│  Cache L1 (Memoria)│     TTL: 30 min
│  Dict em Python    │     Max: 1000 entries
│  pipeline_service  │     Key: hash(numero + tribunal)
└────────┬───────────┘
         │ MISS
         ▼
┌────────────────────┐
│  Cache L2 (SQLite) │     Sem TTL (persistente)
│  resultado_repo    │     Key: numero_processo
│  tabela resultados │
└────────┬───────────┘
         │ MISS
         ▼
    Pipeline IA (busca + analise)
```

---

### 2.7 Scheduler (APScheduler — 2 jobs)

```
┌──────────────────────────────────────────────────┐
│                  APScheduler                      │
│                                                   │
│  Job 1: verificar_saude_fontes                    │
│  ├── Intervalo: 30 minutos                        │
│  ├── Acao: Testa cada fonte (DataJud, DJEN, etc.) │
│  └── Resultado: Grava em health_checks            │
│                                                   │
│  Job 2: executar_captacoes_agendadas              │
│  ├── Intervalo: 5 minutos                         │
│  ├── Acao: Busca captacoes com proxima_execucao   │
│  │         <= agora e status='ativa'              │
│  ├── Filtra: horario permitido + dia da semana    │
│  └── Resultado: Executa busca + grava resultados  │
└──────────────────────────────────────────────────┘
```

---

### 2.8 Autenticacao (JWT + httpOnly Cookies)

```
Login: POST /api/auth/login
       (JSON: username + password)
              │
              ▼
       Verifica bcrypt hash contra users table
              │
              ▼
       Gera JWT (HS256, 60min expiry, PyJWT)
              │
              ▼
       Define cookie httpOnly:
       Set-Cookie: access_token=<jwt>;
         HttpOnly; Secure; SameSite=Lax; Path=/
              │
              ▼
       Frontend NAO armazena token (cookie automatico)
              │
              ▼
       Todas as requests enviam cookie automaticamente
              │
              ▼
       Backend valida via get_current_user():
       1. Verifica cookie httpOnly
       2. Fallback: header Authorization: Bearer <token>
       3. Verifica tenant_id do usuario
```

> IMPORTANTE: Tokens NAO sao armazenados em localStorage (vulneravel a XSS).
> Cookies httpOnly sao inacessiveis via JavaScript.

---

### 2.9 Notificacoes

```
Publicacao encontrada (captacao ou monitor)
              │
              ▼
       ┌──────────────┐
       │  notifier.py │
       ├──────────────┤
       │              │
       ├── WhatsApp ──┼──→ API WhatsApp (a configurar)
       │              │
       └── Email ─────┼──→ SMTP (a configurar)
                      │
                      └──→ Marca publicacao.notificado = True
```

> Nota: As notificacoes por WhatsApp e e-mail dependem de configuracao
> de servicos externos (API WhatsApp Business, servidor SMTP).
> O codigo do notifier.py esta implementado mas os servicos externos
> precisam ser configurados.

---

## 3. Infraestrutura

### 3.1 Docker Compose

```yaml
# docker-compose.yml (simplificado)

services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    restart: unless-stopped
    security_opt: ["no-new-privileges:true"]

  backend:
    build: Dockerfile.backend
    # Porta NAO exposta ao host — apenas via rede Docker
    volumes: captacao-data:/app/data
    env_file: .env
    user: "1000"
    restart: unless-stopped
    security_opt: ["no-new-privileges:true"]

  frontend:
    build: Dockerfile.frontend
    # Porta NAO exposta ao host — apenas via rede Docker
    depends_on: backend
    environment:
      NEXT_PUBLIC_API_URL: https://captacao.jurislaw.com.br
    restart: unless-stopped
    security_opt: ["no-new-privileges:true"]

volumes:
  captacao-data:    # SQLite + dados persistentes
  caddy_data:       # Certificados TLS
```

### 3.2 Caddy (Reverse Proxy + Auto-TLS)

```
Internet → Caddy (:80 redirect → :443 HTTPS)
              │
         ┌────┴────────────────────────┐
         │  captacao.jurislaw.com.br { │
         │    reverse_proxy /api/*     │
         │      backend:8000           │  ← Backend
         │                             │
         │    reverse_proxy /*         │
         │      frontend:3000          │  ← Frontend
         │                             │
         │    header {                 │
         │      Strict-Transport-Sec.  │
         │      X-Frame-Options DENY   │
         │      X-Content-Type nosniff │
         │    }                        │
         │  }                          │
         └─────────────────────────────┘

> TLS automatico via Let's Encrypt (zero config)
> HTTP/2 e HTTP/3 habilitados por padrao
> Security headers injetados pelo Caddy
```

### 3.3 Variaveis de Ambiente

| Variavel | Onde | Descricao |
|----------|------|-----------|
| `ADMIN_USERNAME` | .env | Usuario admin |
| `ADMIN_PASSWORD` | .env | Senha admin (SEM valor padrao) |
| `JWT_SECRET_KEY` | .env | Chave secreta JWT (app recusa iniciar sem) |
| `ENCRYPTION_KEY` | .env | Chave Fernet para criptografia de API keys |
| `DATAJUD_API_KEY` | .env | API Key do DataJud (CNJ, criptografada) |
| `BRIGHTDATA_PROXY_URL` | .env | URL proxy residencial Bright Data |
| `BRIGHTDATA_API_KEY` | .env | API Key Bright Data (criptografada) |
| `BRIGHTDATA_SCRAPING_BROWSER_WS` | .env | WebSocket Scraping Browser |
| `NEXT_PUBLIC_API_URL` | .env / docker | URL publica da API |
| `DOMAIN` | .env | Dominio para TLS do Caddy |
| `ALLOWED_ORIGINS` | .env | Origens CORS permitidas |
| `IS_PRODUCTION` | .env | `true` em producao |
| `CAPTACAO_DB_PATH` | settings.py | Caminho do SQLite (default: /app/data/) |
| `LOG_LEVEL` | settings.py | Nivel de log (INFO) |
| `SCHEDULER_ENABLED` | settings.py | Habilita APScheduler |

> IMPORTANTE: `.env` esta no `.gitignore`. NUNCA commitar credenciais.
> `.env.example` contem template sem valores reais.

---

## 4. Fluxos Principais

### 4.1 Fluxo: Analise de Processo

```
Usuario digita numero → Frontend POST /api/processo/analisar
                              │
                              ▼
                     Backend recebe request
                              │
                    ┌─────────┴──────────┐
                    │ Verifica Cache L1   │
                    │ (memoria, 30min)    │
                    └─────────┬──────────┘
                         HIT? │ MISS
                    ┌─────────┴──────────┐
                    │ Verifica Cache L2   │
                    │ (SQLite)            │
                    └─────────┬──────────┘
                         HIT? │ MISS
                              ▼
                    ┌──────────────────┐
                    │  Pipeline IA     │
                    │  (6 camadas,     │
                    │   14 agentes)    │
                    └────────┬─────────┘
                             │
                    Busca em paralelo:
                    DataJud + DJEN + TJSP + DEJT
                             │
                    Agentes processam dados
                             │
                    Resultado: ProcessoCanonical
                             │
                    Grava Cache L1 + L2
                             │
                    Retorna JSON ao frontend
                             │
                    Frontend renderiza:
                    resumo + timeline + riscos
```

### 4.2 Fluxo: Captacao Automatizada

```
Usuario cria regra → Frontend POST /api/captacao
                          │
                          ▼
                 Backend grava em SQLite (tabela captacoes)
                          │
                          ▼
                 Scheduler (a cada 5 min):
                 "Ha captacoes para executar agora?"
                          │
                    ┌─────┴─────┐
                    │ SIM       │ NAO → aguarda
                    ▼           │
              Verifica:         │
              - horario OK?     │
              - dia OK?         │
              - status ativa?   │
                    │           │
                    ▼           │
              Executa busca     │
              na fonte config.  │
                    │           │
                    ▼           │
              Grava publicacoes │
              encontradas       │
                    │           │
              Grava execucao    │
              no historico      │
                    │           │
              Atualiza contadores
              + proxima_execucao
                    │
              Notifica (se config.)
              WhatsApp / Email
```

### 4.3 Fluxo: Monitor

```
Usuario cria monitorado → POST /api/monitor
                              │
                              ▼
                     Grava em SQLite (tabela monitorados)
                              │
                              ▼
                     Scheduler verificar_saude (30 min):
                     Busca publicacoes para cada monitorado ativo
                              │
                              ▼
                     Novas publicacoes?
                     ├── SIM → Grava em publicacoes (com hash dedup)
                     │         Marca notificado se config.
                     └── NAO → Atualiza ultima_busca
```

---

## 5. Arquivos e Diretorios (Mapa Completo)

```
captacao-blindada/
│
├── backend/                          # BACKEND (Python/FastAPI)
│   ├── requirements.txt              # 15+ dependencias
│   ├── requirements-dev.txt          # pytest, ruff, mypy
│   └── djen/                         # Modulo principal
│       ├── settings.py               # 22+ env vars centralizadas
│       ├── route_manager.py          # Proxy routing por fonte
│       ├── legal_parser.py           # Regex: processos, OABs, CPFs, CNPJs
│       ├── notifier.py               # WhatsApp + Email notifications
│       ├── api/
│       │   ├── app.py                # FastAPI app, lifespan, CORS, scheduler
│       │   ├── auth.py               # JWT httpOnly cookies, bcrypt, RBAC
│       │   ├── crypto.py             # Fernet encryption para API keys
│       │   ├── ratelimit.py          # Rate limiting (slowapi)
│       │   ├── database.py           # SQLite CRUD, 27 tabelas, multi-tenant
│       │   ├── schemas.py            # 30+ Pydantic models + enums
│       │   ├── resultado_repository.py # UPSERT de resultados de analise
│       │   └── routers/
│       │       ├── captacao.py       # 14 endpoints + WebSocket
│       │       ├── datajud.py        # 4 endpoints
│       │       ├── djen_router.py    # 7 endpoints
│       │       ├── health.py         # 1 endpoint
│       │       ├── monitor.py        # 7 endpoints
│       │       ├── processo.py       # 14 endpoints + WebSocket
│       │       ├── validation.py     # 5 endpoints (CNJ, OAB)
│       │       ├── webhook.py        # 5 endpoints
│       │       ├── metrics.py        # 4 endpoints
│       │       ├── ia_config.py      # 5+ endpoints (IA config)
│       │       ├── admin/            # 20+ endpoints (usuarios, audit, tenants)
│       │       └── ... (37+ routers total)
│       ├── sources/
│       │   ├── base.py               # BaseSource ABC + PublicacaoResult
│       │   ├── datajud.py            # DataJud API (60+ tribunais)
│       │   ├── djen_source.py        # DJEN API (proxy BR obrigatorio)
│       │   ├── tjsp_dje.py           # TJSP DJe web scraper (JSF)
│       │   ├── dejt.py               # DEJT web scraper (JSF)
│       │   ├── querido_diario.py     # Querido Diario REST API
│       │   └── jusbrasil.py          # JusBrasil via Bright Data
│       ├── agents/
│       │   ├── canonical_model.py    # ProcessoCanonical (50+ campos)
│       │   ├── orchestrator.py       # Registro + orquestracao de agentes
│       │   ├── specialized.py        # 14 agentes heuristicos (6 camadas)
│       │   ├── ml_agents.py          # 4 agentes LLM com fallback
│       │   ├── sanitize.py           # Sanitizacao anti-prompt-injection
│       │   ├── pipeline_service.py   # Pipeline facade, cache L1, tracker
│       │   └── captacao_service.py   # Servico de captacao automatizada
│       ├── config/
│       │   └── tribunais_dje.json    # 60+ tribunais mapeados
│       ├── tests/                    # 9 arquivos de testes
│       └── scripts/                  # 6 scripts utilitarios
│
├── frontend/                         # FRONTEND (Next.js/React)
│   ├── package.json                  # Dependencias Node.js
│   ├── next.config.ts                # Proxy /api → backend:8000
│   ├── tailwind.config.ts            # Tema legal/gold/risco
│   ├── tsconfig.json                 # TypeScript strict mode
│   ├── playwright.config.ts          # E2E testing config
│   ├── e2e/                          # 8 arquivos Playwright
│   └── src/
│       ├── app/
│       │   ├── globals.css           # CSS vars (light/dark)
│       │   ├── layout.tsx            # Root server layout
│       │   ├── client-layout.tsx     # Auth guard + Sidebar wrapper
│       │   ├── page.tsx              # Dashboard (/)
│       │   ├── login/page.tsx        # Login (/login)
│       │   ├── processo/page.tsx     # Analise IA (/processo)
│       │   ├── processo/[numero]/    # Detalhe (/processo/[numero])
│       │   ├── busca/page.tsx        # Busca unificada (/busca)
│       │   ├── monitor/page.tsx      # Monitor (/monitor)
│       │   └── captacao/page.tsx     # Captacao (/captacao)
│       ├── components/               # 6 componentes reutilizaveis
│       └── lib/                      # api.ts, auth-context, utils
│
├── docs/                             # DOCUMENTACAO
│   ├── TECNICO_PROGRAMADOR.md        # Doc tecnico (~654 linhas)
│   ├── GUIA_USUARIO.md               # Guia do usuario
│   └── MAPEAMENTO_SISTEMA.md         # Este documento
│
├── docker-compose.yml                # 3 services (caddy + backend + frontend) + 2 volumes
├── Caddyfile                         # Reverse proxy config (auto-TLS)
├── Dockerfile.backend                # Python 3.11-slim-bookworm, non-root
├── Dockerfile.frontend               # Node 20-alpine, standalone
├── Dockerfile                        # All-in-one (alternativo)
├── Makefile                          # 12 comandos dev/test/deploy
├── pyproject.toml                    # pytest/ruff/mypy config
├── .env.example                      # Template de env vars
└── scripts/
    ├── setup.sh                      # Setup Linux/macOS
    └── setup.ps1                     # Setup Windows
```

---

## 6. Metricas do Projeto

| Metrica | Valor |
|---------|-------|
| Total de arquivos Python (backend) | ~49 |
| Total de linhas Python | ~8.700 |
| Total de arquivos TypeScript (frontend) | ~16 |
| Endpoints REST | 120+ |
| WebSockets | 2 |
| Tabelas SQLite | 27 |
| Agentes IA | 14 (10 heuristicos + 4 ML) |
| Fontes de dados | 7 |
| Componentes React | 16 |
| Paginas Next.js | 15 |
| Testes backend | 9 arquivos (288/294 passando) |
| Testes E2E | 8 specs Playwright |
| Routers backend | 37+ |
| Security layers | 7 (auth, tenant, rate limit, crypto, sanitize, headers, TLS) |

---

## 7. Problemas Conhecidos e Limitacoes

| # | Problema | Status | Impacto |
|---|----------|--------|---------|
| 1 | DJEN requer proxy BR (IP alemao bloqueado) | Resolvido (Bright Data) | Alto |
| 2 | TJSP DJe scraper pode quebrar se layout mudar | Risco | Medio |
| 3 | DEJT scraper pode quebrar se layout mudar | Risco | Medio |
| 4 | JusBrasil scraping depende de Bright Data Web Unlocker | Risco | Medio |
| 5 | Notificacoes WhatsApp/Email nao configuradas | Pendente | Medio |
| 6 | ~~Sem rate limiting nos endpoints~~ | Resolvido v3.0.0 | ~~Baixo~~ |
| 7 | Sem backup automatico do SQLite | Pendente | Alto |
| 8 | Agentes ML (LLM) dependem de API externa | Risco | Baixo (fallback) |
| 9 | ~~Sem multi-tenancy (usuario unico admin)~~ | Resolvido v3.0.0 | ~~Medio~~ |
| 10 | ~~JWT em localStorage (vulneravel a XSS)~~ | Resolvido v3.0.0 (httpOnly) | ~~Alto~~ |
| 11 | ~~Nginx manual SSL~~ | Resolvido v3.0.0 (Caddy auto-TLS) | ~~Medio~~ |
| 12 | ~~Sem criptografia de API keys~~ | Resolvido v3.0.0 (Fernet) | ~~Alto~~ |
| 13 | ~~Sem sanitizacao anti-prompt-injection~~ | Resolvido v3.0.0 | ~~Alto~~ |

---

## 8. Historico de Mudancas (Sessao Atual)

| Data | Mudanca |
|------|---------|
| 2026-04-26 | v3.0.0 Security Hardening: Caddy auto-TLS, httpOnly cookies, Fernet encryption, rate limiting, multi-tenant, sanitizacao |
| 2026-04-14 | Corrigidos 12 bugs criticos no backend e frontend |
| 2026-04-14 | Construida pagina de Captacao Automatizada (~1010 linhas) |
| 2026-04-14 | Fix proxy DJEN via RouteManager (djen_api → residential_proxy) |
| 2026-04-14 | Fix CORS credentials + origin |
| 2026-04-14 | Fix Pydantic v2 schemas (example → json_schema_extra) |
| 2026-04-14 | Fix login form-urlencoded |
| 2026-04-14 | Fix busca unificada (shape, params, error handling) |
| 2026-04-14 | Fix resultado truncation, datas invalidas, movimentos |
| 2026-04-14 | Fix monitor publicacoes viewer |
| 2026-04-14 | Documentacao: tecnico, usuario, mapeamento |

---

*Documento gerado em 2026-04-14 — Captacao Peticao Blindada v1.1.0*

---

## Mapeamento v2.0.0 - Novos Routers e Endpoints

### Routers Adicionados (v1.2.1 → v2.0.0)

| Router | Prefixo | Endpoints | Descrição |
|--------|---------|-----------|-----------|
| validation | /api/validation | 5 | Validação CNJ, OAB, Tribunais |
| webhooks | /api/webhooks | 5 | Webhooks CRUD e trigger |
| metrics | /api/metrics | 4 | Métricas JSON e Prometheus |
| advanced | /api/config | 15 | API Keys, 2FA, SSO, Cache, Backup, Settings, Purge |
| notifications | /api/notifications | 3 | Email e WhatsApp |
| dashboard | /api/dashboard | 6 | Evolução, tribunais, fontes, próximas, atividade |
| relatorios | /api/relatorios | 3 | Semanal, diário, CSV |
| busca_unificada | /api/busca | 2 | Busca simultânea e status fontes |
| prazos | /api/prazos | 5 | Prazos processuais CRUD |
| favoritos | /api/favoritos | 7 | Favoritos e tags |
| agenda | /api/agenda | 5 | Compromissos e audiências |
| contadores | /api/contadores | 1 | Contadores em tempo real |
| busca_global | /api/busca-global | 1 | Busca full-text global |
| atividades | /api/atividades | 3 | Atividades, email HTML, duplicatas |
| sistema | /api/sistema | 4 | Versão, changelog, exportar, tabelas |
| analytics | /api/analytics | 7 | Publicações/dia, tribunais, horas pico |
| extras | /api/extras | 9 | Batch insert, duplicadas, saúde completa |
| tools | /api/tools | 6 | Formatar CNJ, dias úteis, vacuum |
| integracoes | /api/integracoes | 6 | Telegram, webhook receiver, status |
| automacoes | /api/automacoes | 6 | Regras de automação CRUD |
| fontes_config | /api/fontes | 3 | Configuração de 10 fontes de dados |
| kanban | /api/kanban | 8 | Kanban board CRUD |
| final_batch | /api/v2 | 13 | Comparação, score, heatmap, notas, templates |

### Tabelas do Banco (27 total)

| Tabela | Descrição |
|--------|-----------|
| captacoes | Captações automatizadas |
| execucoes_captacao | Histórico de execuções |
| publicacoes | Publicações encontradas |
| users | Usuários do sistema |
| tenants | Escritórios/empresas |
| audit_logs | Cadeia de custódia |
| system_errors | Erros do sistema |
| ai_config | Configuração de IA |
| buscas | Histórico de buscas |
| monitorados | Itens monitorados |
| processos_monitorados | Processos monitorados |
| health_checks | Verificações de saúde |
| function_costs | Custos por função |
| usage_logs | Logs de uso/tarifação |
| resultados_analise | Resultados de análise IA |
| processo_anotacoes | Anotações em processos |
| prazos | Prazos processuais |
| agenda | Compromissos/audiências |
| favoritos | Favoritos |
| tags | Tags/etiquetas |
| tag_associacoes | Associações de tags |
| kanban_cards | Cards do Kanban |
| automacao_regras | Regras de automação |
| automacao_historico | Histórico de automações |
| notas_globais | Notas/lembretes |
| webhook_received | Webhooks recebidos |
| ia_logs | Log de chamadas IA |

### Componentes Frontend (15 páginas + 10 componentes)

| Componente | Arquivo | Descrição |
|-----------|---------|-----------|
| Toast | components/Toast.tsx | Notificações visuais |
| Skeleton | components/Skeleton.tsx | Loading states |
| Modal | components/Modal.tsx | Modais e confirmações |
| Breadcrumbs | components/Breadcrumbs.tsx | Navegação hierárquica |
| EmptyState | components/EmptyState.tsx | Estados vazios |
| CompactTable | components/CompactTable.tsx | Tabelas compactas |
| Tooltip | components/Tooltip.tsx | Tooltips informativos |
| OnlineIndicator | components/OnlineIndicator.tsx | Indicador offline |
| KeyboardShortcutsHelp | components/KeyboardShortcutsHelp.tsx | Atalhos de teclado |

### Hooks Customizados

| Hook | Arquivo | Descrição |
|------|---------|-----------|
| useDebounce | hooks/useDebounce.ts | Debounce para campos de busca |
| useLocalStorage | hooks/useLocalStorage.ts | Estado persistido em localStorage |
| useOnlineStatus | hooks/useOnlineStatus.ts | Status de conexão |
| useKeyboardShortcuts | hooks/useKeyboardShortcuts.ts | Atalhos de teclado |

---

## Melhorias v2.1.0 (2026-04-24) — 31 implementações

### Frontend — UX Melhorada

| Melhoria | Arquivo | Descrição |
|----------|---------|-----------|
| Badges de fonte diferenciados | captacao, monitor, busca | Azul para DataJud, âmbar para DJEN em todos os pontos |
| Resultados clicáveis | captacao, monitor, busca | numero_processo é Link para /processo?q=... |
| Cards expandíveis | captacao, monitor, processo | Clique para ver detalhes completos |
| Paginação "Carregar mais" | captacao (20), monitor (30), processos (30), timeline (30) | Evita renderizar centenas de itens |
| Filtro por fonte | captacao, busca | Botões DataJud/DJEN/Todas com contagem |
| Tracking lidos/não-lidos | captacao, processo | localStorage com badge pulsante |
| Deep links do Dashboard | captacao?filter=novos, processo?filter=recente | Navegação direta para resultados relevantes |
| Validação CNJ | processo | Regex no formulário de adicionar processo |
| Exportação CSV/JSON | processo | Download client-side dos processos monitorados |
| Feriados dinâmicos | monitor | Cálculo automático de Páscoa + feriados móveis |
| Checkboxes de fonte | busca | DataJud/DJEN respeitados na busca unificada |
| Contagem por fonte | busca | Badges com total por fonte nos resultados |
| DJEN expandível na Análise | processo | Cards DJEN clicáveis e expandíveis |
| Indicador data indisponível | processo | Badge âmbar com AlertTriangle na timeline |
| ESLint configurado | frontend | next/core-web-vitals + regras customizadas |

### Backend — Melhorias

| Melhoria | Arquivo | Descrição |
|----------|---------|-----------|
| Filtro ?fonte= | database.py | Endpoint publicações aceita filtro por fonte (IN query) |
| Diff hash movimentações | app.py | Detecta movimentações realmente novas via hash comparison |
| Advogado/parte salvam no banco | djen_router.py | Endpoints /advogado e /parte agora persistem resultados |
| novas_movimentacoes corretas | app.py | Cálculo real em vez de hardcoded 0 |
| Detalhes no histórico | app.py | Inclui data/nome das novas movimentações |                                       