# Mapeamento do Sistema — Captacao Peticao Blindada

> Versao: 1.1.0 | Atualizado: 2026-04-14 | Para: Equipe tecnica e gestao

---

## 1. Visao Geral

```
                          INTERNET
                             |
                  captacao.jurislaw.com.br
                       (DNS A Record)
                             |
                  ┌──────────────────────┐
                  │  Contabo VPS         │
                  │  207.180.199.121     │
                  │  Ubuntu / Docker     │
                  │                      │
                  │  ┌────────────────┐  │
                  │  │  Nginx         │  │
                  │  │  :80 → :443   │  │
                  │  │  SSL/TLS      │  │
                  │  └──────┬─────────┘  │
                  │         │            │
                  │    ┌────┴────┐       │
                  │    │        │       │
                  │  ┌─┴──┐  ┌─┴──┐    │
                  │  │FE  │  │BE  │    │
                  │  │8010│  │8001│    │
                  │  └────┘  └─┬──┘    │
                  │            │       │
                  │     ┌──────┴──┐    │
                  │     │ SQLite  │    │
                  │     │ (vol)   │    │
                  │     └─────────┘    │
                  └──────────────────────┘
                             │
               ┌─────────────┼─────────────┐
               │             │             │
          ┌────┴────┐  ┌────┴────┐  ┌────┴────┐
          │ DataJud │  │  DJEN   │  │ Bright  │
          │  (CNJ)  │  │  (CNJ)  │  │  Data   │
          │ API Key │  │ via BR  │  │  Proxy  │
          └─────────┘  │ Proxy   │  └─────────┘
                       └─────────┘
```

---

## 2. Componentes do Sistema

### 2.1 Frontend (Next.js)

| Atributo | Valor |
|----------|-------|
| Framework | Next.js 15.1.0 + React 19 + TypeScript 5.7 |
| UI | Tailwind CSS 3.4 + Radix UI + Lucide Icons |
| HTTP Client | Axios 1.7.9 (ApiClient singleton) |
| Container | Node 20 Alpine, porta 8010 |
| Build mode | Standalone (next build → standalone output) |

#### Paginas (7 rotas)

| Rota | Arquivo | Funcao |
|------|---------|--------|
| `/` | `app/page.tsx` | Dashboard — visao geral, stats, processos recentes |
| `/login` | `app/login/page.tsx` | Autenticacao com usuario/senha |
| `/processo` | `app/processo/page.tsx` | Analise de processos com IA |
| `/processo/[numero]` | `app/processo/[numero]/page.tsx` | Detalhe de processo especifico |
| `/busca` | `app/busca/page.tsx` | Busca unificada em multiplas fontes |
| `/monitor` | `app/monitor/page.tsx` | Monitoramento de processos/OABs |
| `/captacao` | `app/captacao/page.tsx` | Captacao automatizada de publicacoes |

#### Componentes (6)

| Componente | Arquivo | Funcao |
|------------|---------|--------|
| `Sidebar` | `components/Sidebar.tsx` | Menu lateral colapsavel + dark mode + logout |
| `LoadingSpinner` | `components/LoadingSpinner.tsx` | Spinner animado com texto (sm/default/lg) |
| `ProcessoCard` | `components/ProcessoCard.tsx` | Card de processo com resumo |
| `RiskBadge` + `RiskGauge` | `components/RiskBadge.tsx` | Badge e gauge visual de risco (0-100) |
| `StatsCard` | `components/StatsCard.tsx` | Card de estatistica com icone e tendencia |
| `TimelineView` | `components/TimelineView.tsx` | Linha do tempo de movimentacoes |

#### Bibliotecas (lib/)

| Arquivo | Funcao |
|---------|--------|
| `api.ts` | ApiClient singleton com 30+ metodos e 20+ interfaces |
| `auth-context.tsx` | React Context para autenticacao (login, logout, user, token) |
| `utils.ts` | Utilitario `cn()` (clsx + tailwind-merge) |

---

### 2.2 Backend (FastAPI)

| Atributo | Valor |
|----------|-------|
| Framework | FastAPI + Uvicorn + Pydantic v2 |
| Linguagem | Python 3.12 |
| Container | python:3.12-slim, porta 8001, user non-root |
| Banco | SQLite com WAL mode |
| Scheduler | APScheduler (2 jobs periodicos) |

#### Endpoints (45+ total, 6 routers)

| Router | Prefixo | Endpoints | Funcao |
|--------|---------|-----------|--------|
| `captacao.py` | `/api/captacao` | 14 + WS | CRUD + execucao de captacoes automatizadas |
| `processo.py` | `/api/processo` | 14 + WS | Analise, resumo, timeline, riscos, comparacao |
| `monitor.py` | `/api/monitor` | 7 | CRUD de monitorados + publicacoes + stats |
| `djen_router.py` | `/api/djen` | 7 | Busca DJEN, publicacoes, tribunais |
| `datajud.py` | `/api/datajud` | 4 | Busca DataJud, detalhes de processo |
| `health.py` | `/api/health` | 1 | Health check com status de fontes |
| `auth.py` | `/api/auth` | 3 | Login, me, token refresh |

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

### 2.8 Autenticacao (JWT)

```
Login: POST /api/auth/token
       (form-urlencoded: username + password)
              │
              ▼
       Verifica bcrypt hash contra user store
              │
              ▼
       Gera JWT (HS256, 60min expiry)
              │
              ▼
       Retorna: { access_token, token_type }
              │
              ▼
       Frontend armazena em localStorage
              │
              ▼
       Todas as requests incluem:
       Authorization: Bearer <token>
              │
              ▼
       Backend valida token via get_current_user()
```

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
  backend:
    build: Dockerfile.backend
    ports: "127.0.0.1:8001:8000"
    volumes: captacao-data:/app/data
    env_file: .env
    restart: unless-stopped

  frontend:
    build: Dockerfile.frontend
    ports: "127.0.0.1:8010:3000"
    depends_on: backend
    environment:
      NEXT_PUBLIC_API_URL: https://captacao.jurislaw.com.br
    restart: unless-stopped

volumes:
  captacao-data:    # SQLite + dados persistentes
```

### 3.2 Nginx (Reverse Proxy)

```
Internet → :443 (SSL)
              │
         ┌────┴────────────────────────┐
         │  location / {               │
         │    proxy_pass :8010;        │  ← Frontend
         │  }                          │
         │                             │
         │  location /api/ {           │
         │    proxy_pass :8001;        │  ← Backend
         │  }                          │
         │                             │
         │  location /ws/ {            │
         │    proxy_pass :8001;        │  ← WebSocket
         │    upgrade WebSocket;       │
         │  }                          │
         └─────────────────────────────┘
```

### 3.3 Variaveis de Ambiente

| Variavel | Onde | Descricao |
|----------|------|-----------|
| `ADMIN_USERNAME` | .env | Usuario admin |
| `ADMIN_PASSWORD` | .env | Senha admin (bcrypt) |
| `JWT_SECRET_KEY` | .env | Chave secreta para tokens JWT |
| `DATAJUD_API_KEY` | .env | API Key do DataJud (CNJ) |
| `BRIGHT_DATA_PROXY_USERNAME` | .env | Credencial Bright Data |
| `BRIGHT_DATA_PROXY_PASSWORD` | .env | Credencial Bright Data |
| `BRIGHT_DATA_API_KEY` | .env | API Key Bright Data |
| `NEXT_PUBLIC_API_URL` | .env / docker | URL publica da API |
| `DATABASE_PATH` | settings.py | Caminho do SQLite (default: /app/data/) |
| `LOG_LEVEL` | settings.py | Nivel de log (INFO) |
| `CORS_ORIGINS` | settings.py | Origens CORS permitidas |
| `SCHEDULER_ENABLED` | settings.py | Habilita APScheduler |

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
│       │   ├── auth.py               # JWT, bcrypt, login endpoint
│       │   ├── database.py           # SQLite CRUD, 7 tabelas, ~630 linhas
│       │   ├── schemas.py            # 30+ Pydantic models + enums
│       │   ├── resultado_repository.py # UPSERT de resultados de analise
│       │   └── routers/
│       │       ├── captacao.py       # 14 endpoints + WebSocket
│       │       ├── datajud.py        # 4 endpoints
│       │       ├── djen_router.py    # 7 endpoints
│       │       ├── health.py         # 1 endpoint
│       │       ├── monitor.py        # 7 endpoints
│       │       └── processo.py       # 14 endpoints + WebSocket
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
├── docker-compose.yml                # 2 services + 1 volume
├── Dockerfile.backend                # Python 3.12-slim, non-root
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
| Endpoints REST | 45+ |
| WebSockets | 2 |
| Tabelas SQLite | 7 |
| Agentes IA | 14 (11 heuristicos + 4 ML) |
| Fontes de dados | 7 |
| Componentes React | 6 |
| Paginas Next.js | 7 |
| Testes backend | 9 arquivos |
| Testes E2E | 8 specs Playwright |

---

## 7. Problemas Conhecidos e Limitacoes

| # | Problema | Status | Impacto |
|---|----------|--------|---------|
| 1 | DJEN requer proxy BR (IP alemao bloqueado) | Resolvido (Bright Data) | Alto |
| 2 | TJSP DJe scraper pode quebrar se layout mudar | Risco | Medio |
| 3 | DEJT scraper pode quebrar se layout mudar | Risco | Medio |
| 4 | JusBrasil scraping depende de Bright Data Web Unlocker | Risco | Medio |
| 5 | Notificacoes WhatsApp/Email nao configuradas | Pendente | Medio |
| 6 | Sem rate limiting nos endpoints | Pendente | Baixo |
| 7 | Sem backup automatico do SQLite | Pendente | Alto |
| 8 | Agentes ML (LLM) dependem de API externa | Risco | Baixo (fallback) |
| 9 | Sem multi-tenancy (usuario unico admin) | Design | Medio |

---

## 8. Historico de Mudancas (Sessao Atual)

| Data | Mudanca |
|------|---------|
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
