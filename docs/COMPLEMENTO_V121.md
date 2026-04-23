# Complemento de Implementações — Captacao Peticao Blindada

> Versao: 1.4.0 | Atualizado: 2026-04-23 | Para: Desenvolvedores e DevOps

---

Este documento complementa os documentos existentes com todas as implementações adicionadas nas versões 1.2.1 e 1.3.0.

---

## 1. Segurança

### 1.1 Rate Limiting
**Arquivo:** `backend/djen/api/ratelimit.py`

| Endpoint | Limite |
|----------|--------|
| `/api/auth/login` | 5 req/min |
| `/api/datajud/buscar` | 30 req/min |
| `/api/captacao/executar-todas` | 5 req/min |
| **Geral** | 60 req/min |

### 1.2 Circuit Breaker
**Arquivo:** `backend/djen/api/circuitbreaker.py`

| Parâmetro | Valor |
|----------|-------|
| Falhas para abrir | 5 |
| Timeout aberto | 60s |
| Sucessos para fechar | 2 |

### 1.3 Security Headers (v1.3.0)
**Arquivo:** `backend/djen/api/app.py`

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 1.4 CORS Restrito (v1.3.0)
- Produção: configurável via `ALLOWED_ORIGINS` no .env
- Métodos: GET, POST, PUT, DELETE, OPTIONS
- Headers expostos: X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After

### 1.5 Bloqueio de Login (v1.3.0)
- 5 tentativas falhadas = bloqueio por 5 minutos
- Registro de tentativas falhadas na auditoria
- Limpeza automática após login bem-sucedido

### 1.6 JWT Obrigatório em Produção
- `IS_PRODUCTION=true` exige `JWT_SECRET_KEY`
- Sistema não inicia sem chave em produção

---

## 2. Validação de Campos

### 2.1 CNJ, OAB e Tribunais
**Arquivo:** `backend/djen/api/validation.py`

```
GET  /api/validation/tribunais           # 62 tribunais
GET  /api/validation/tribunais/{sigla}   # Verificar tribunal
POST /api/validation/cnj                 # Validar CNJ
POST /api/validation/oab                 # Validar OAB
POST /api/validation/validar-tudo        # Validar múltiplos
```

---

## 3. Webhooks
**Arquivo:** `backend/djen/api/webhook.py`

| Evento | Descrição |
|--------|----------|
| `new_publication` | Nova publicação encontrada |
| `captacao_completed` | Captação finalizada |
| `new_result` | Novo resultado de análise |

```
GET    /api/webhooks              # Listar
POST   /api/webhooks              # Criar
DELETE /api/webhooks/{id}         # Remover
POST   /api/webhooks/test         # Testar
POST   /api/webhooks/trigger/{event}  # Disparar
```

---

## 4. Métricas e Monitoramento
**Arquivo:** `backend/djen/api/metrics.py`

```
GET  /api/metrics             # JSON
GET  /api/metrics/prometheus  # Formato Prometheus
GET  /api/metrics/health      # Health com métricas
POST /api/metrics/reset       # Resetar
```

Middleware automático coleta: requests_total, duration_avg/p50/p95/p99, error_rate.

---

## 5. IA & Modelos (Gemini)
**Arquivo:** `backend/djen/api/routers/ai_config.py`

### Modelos Disponíveis:
| Modelo | Descrição |
|--------|----------|
| `gemini-2.5-flash` | Rápido e versátil |
| `gemini-3-flash-preview` | Última geração com thinking |
| `gemini-2.5-flash-lite` | Ultra leve e econômico |

### Funções de IA:
| Função | Modelo Padrão |
|--------|--------------|
| Classificação Jurídica | gemini-2.5-flash |
| Previsão de Resultado | gemini-3-flash-preview |
| Resumo Executivo | gemini-2.5-flash |
| Análise de Jurisprudência | gemini-3-flash-preview |

```
GET  /ai/config          # Listar configs
GET  /ai/models          # Modelos disponíveis
GET  /ai/functions       # Funções com descrições
PUT  /ai/config/{key}    # Atualizar
POST /ai/test            # Testar conexão
```

---

## 6. Configurações Avançadas
**Arquivo:** `backend/djen/api/routers/advanced.py`

### API Keys
```
GET    /api/config/keys          # Listar
POST   /api/config/keys          # Criar
DELETE /api/config/keys/{id}     # Revogar
```

### 2FA (Opcional)
```
POST /api/config/2fa/generate    # Gerar QR
POST /api/config/2fa/verify      # Verificar
```

### SSO/SAML (Opcional)
```
GET  /api/config/sso             # Status
POST /api/config/sso             # Configurar
```

### Cache
```
GET  /api/config/cache/stats     # Estatísticas
POST /api/config/cache/clear     # Limpar
POST /api/config/cache/redis     # Conectar Redis
```

### Backup
```
GET  /api/config/backup                    # Listar
POST /api/config/backup                    # Criar
POST /api/config/backup/{name}/restore     # Restaurar
POST /api/config/backup/auto/start         # Iniciar automático
POST /api/config/backup/auto/stop          # Parar
```

---

## 7. Notificações (v1.3.0)
**Arquivo:** `backend/djen/api/notifications.py`

### Canais:
- Email (SMTP) - configurável via .env
- WhatsApp Business API - configurável via .env

### Variáveis de Ambiente:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=email@gmail.com
SMTP_PASSWORD=app-password
SMTP_FROM=email@gmail.com
NOTIFICATION_EMAIL=destino@email.com

WHATSAPP_TOKEN=token
WHATSAPP_PHONE_ID=phone-id
NOTIFICATION_WHATSAPP=5511999999999
```

### Endpoints:
```
GET  /api/notifications/status       # Status dos canais
POST /api/notifications/test/email   # Testar email
POST /api/notifications/test/whatsapp # Testar WhatsApp
```

---

## 8. Exportação de Dados (v1.3.0)

### Publicações:
```
GET /api/monitor/publicacoes/export/csv   # CSV
GET /api/monitor/publicacoes/export/json  # JSON
```

### Cadeia de Custódia:
```
GET /api/audit/export/csv    # CSV
GET /api/audit/export/json   # JSON
```

---

## 9. Funcionalidades de Publicações (v1.3.0)

### Marcar como Lida/Favorita:
```
PUT /api/monitor/publicacoes/{id}/lida      # Marcar lida
PUT /api/monitor/publicacoes/{id}/favorita  # Favoritar
```

---

## 10. Captação Melhorada (v1.3.0)

### Clonar Captação:
```
POST /api/captacao/{id}/clonar   # Cria cópia
```

### Busca Paginada DJEN:
- Até 10 páginas por execução = 1000 resultados
- Vinculação automática de publicações ao captacao_id

---

## 11. Cadeia de Custódia Melhorada (v1.3.0)

### Auditoria Automática:
- Middleware registra automaticamente todas as ações POST/PUT/DELETE
- Extrai IP, user_id e tenant_id do token JWT

### Estatísticas:
```
GET /api/audit/stats   # Por ação, entidade, usuário
```

### Exportação:
```
GET /api/audit/export/csv    # CSV com filtros
GET /api/audit/export/json   # JSON com filtros
```

---

## 12. UX Melhorada (v1.3.0)

### Novos Componentes:
| Componente | Arquivo | Descrição |
|-----------|---------|----------|
| Toast | `components/Toast.tsx` | Notificações visuais (success/error/warning/info) |
| Skeleton | `components/Skeleton.tsx` | Loading states (text/card/table/circle) |
| Modal | `components/Modal.tsx` | Modais e confirmações |

### Melhorias:
- Usuários: Modal de criar/editar/deletar (substituiu prompt())
- Modo escuro: cores melhoradas, transições, sombras
- Responsividade: padding adaptativo mobile
- Botão Admin Master: navega para Gestão de Usuários
- Tarifação: reformulada com 20 funções do sistema em 4 categorias

---

## 13. Performance (v1.3.0)

### SQLite Otimizado:
```sql
PRAGMA journal_mode=WAL
PRAGMA cache_size=-20000
PRAGMA synchronous=NORMAL
PRAGMA temp_store=MEMORY
PRAGMA mmap_size=268435456
```

### Índices Adicionais:
```sql
CREATE INDEX idx_audit_logs_criado ON audit_logs(criado_em)
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id)
CREATE INDEX idx_system_errors_criado ON system_errors(criado_em)
```

---

## 14. Páginas do Sistema

| Rota | Página | Status |
|------|--------|--------|
| `/` | Dashboard | ✅ |
| `/captacao` | Captação Automatizada | ✅ |
| `/monitor` | DJEN Monitor | ✅ |
| `/processo` | Processos | ✅ |
| `/busca` | Pesquisa Pontual | ✅ |
| `/configuracao-ia` | IA & Modelos | ✅ |
| `/admin/tarifacao` | Tarifação | ✅ |
| `/admin/usuarios` | Gestão de Usuários | ✅ |
| `/admin/tenants` | Cadastros/Tenants | ✅ |
| `/admin/auditoria` | Cadeia de Custódia | ✅ |
| `/admin/erros` | Erros do Sistema | ✅ |

---

## 15. Estrutura de Arquivos (v1.3.0)

```
backend/djen/api/
├── app.py                    # FastAPI + middlewares (security, metrics, audit)
├── auth.py                   # JWT + bloqueio de login
├── database.py               # SQLite otimizado (WAL, cache, mmap)
├── ratelimit.py              # Rate Limiting (slowapi)
├── circuitbreaker.py         # Circuit Breaker
├── validation.py             # Validação CNJ/OAB/Tribunais
├── webhook.py                # Webhooks
├── metrics.py                # Métricas
├── cache.py                  # Cache (Redis opcional)
├── backup.py                 # Backup automático
├── security.py               # API Keys, 2FA, SSO
├── advanced_logging.py       # Log estruturado
├── notifications.py          # Email + WhatsApp
├── audit.py                  # Auditoria hash-chain
└── routers/
    ├── captacao.py           # + clonar, cache, paginação
    ├── datajud.py            # + circuit breaker
    ├── monitor.py            # + exportação, lida/favorita
    ├── validation.py         # Tribunais, CNJ, OAB
    ├── webhooks.py           # Webhooks CRUD
    ├── metrics.py            # Métricas JSON/Prometheus
    ├── advanced.py           # Keys, 2FA, SSO, Cache, Backup
    ├── notifications.py      # Email, WhatsApp
    ├── audit.py              # + stats, exportação CSV/JSON
    └── errors.py             # + /recent

frontend/src/
├── components/
│   ├── Toast.tsx             # Notificações visuais
│   ├── Skeleton.tsx          # Loading states
│   ├── Modal.tsx             # Modais e confirmações
│   ├── Sidebar.tsx           # + Admin Master funcional
│   └── ...
├── app/
│   ├── admin/tenants/        # NOVA página
│   ├── admin/usuarios/       # Reformulada com Modal
│   ├── admin/tarifacao/      # Reformulada com 20 funções
│   ├── admin/auditoria/      # + exportação, stats, filtros
│   └── ...
└── lib/
    └── api.ts                # + getAuditStats, AIProvider.details
```

---

## 16. Deploy

### Variáveis de Ambiente (Produção):
```bash
IS_PRODUCTION=true
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ADMIN_PASSWORD=senha-forte
CAPTACAO_PORT=8001
FRONTEND_PORT=8010
ALLOWED_ORIGINS=https://captacao.jurislaw.com.br
```

### Docker:
```bash
docker compose build --no-cache
docker compose up -d
```

### Healthcheck:
- Endpoint: `/api/metrics/health` (leve, sem fontes externas)
- Intervalo: 60s, Timeout: 15s, Start period: 120s

---

> Versão 1.3.0 - 22/04/2026
