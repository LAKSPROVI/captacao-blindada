# Complemento de Implementações — Captacao Peticao Blindada

> Versao: 1.2.1 | Atualizado: 2026-04-20 | Para: Desenvolvedores e DevOps

---

Este documento complementa os documentos existentes com as novas implementações adicionadas na versão 1.2.1.

---

## 1. Novas Funcionalidades de Segurança

### 1.1 Rate Limiting

**Arquivo:** `backend/djen/api/ratelimit.py`

| Endpoint | Limite |
|----------|--------|
| `/api/auth/login` | 5 req/min |
| `/api/datajud/buscar` | 30 req/min |
| `/api/djen/buscar` | 30 req/min |
| `/api/captacao/executar-todas` | 5 req/min |
| **Geral** | 60 req/min |

**Headers de resposta:**
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
Retry-After: 45
```

**Dependência:** `slowapi>=0.1.6`

---

### 1.2 Circuit Breaker

**Arquivo:** `backend/djen/api/circuitbreaker.py`

Proteção automática contra falhas em cascade:

| Parâmetro | Valor |
|----------|-------|
| Falhas para abrir | 5 |
| Timeout aberto | 60s |
| Sucessos para fechar | 2 |

**Endpoints de monitoramento:**
```
GET /api/health/circuits           # Status dos circuits
POST /api/health/circuits/reset   # Resetar
```

---

### 1.3 Autenticação em Produção

**Arquivo:** `backend/djen/api/auth.py`

**Variáveis obrigaqtórias em produção:**
```bash
export IS_PRODUCTION=true
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

Se `IS_PRODUCTION=true` e `JWT_SECRET_KEY` não estiver configurada, o sistema **NÃO INICIARÁ**.

---

## 2. Validação de Campos

### 2.1 CNJ e OAB

**Arquivo:** `backend/djen/api/validation.py`

**Endpoints:**
```
GET  /api/validation/tribunais           # Lista tribunais
GET  /api/validation/tribunais/{sigla}   # Verificar tribunal
POST /api/validation/cnj                  # Validar CNJ
POST /api/validation/oab                # Validar OAB
POST /api/validation/validar-tudo      # Validar múltiplos
```

**Exemplo de resposta - Tribunais:**
```json
{
  "tribunais": [
    {"sigla": "tjsp", "nome": "Tribunal de Justiça de São Paulo", "tipo": "estadual"},
    {"sigla": "tjrj", "nome": "Tribunal de Justiça do Rio de Janeiro", "tipo": "estadual"}
  ]
}
```

---

## 3. Webhooks

**Arquivo:** `backend/djen/api/webhook.py`

Notificações automáticas quando eventos acontecem:

| Evento | Descrição |
|--------|------------|
| `new_publication` | Nova publicação encontrada |
| `captacao_completed` | Captação finalizada |
| `new_result` | Novo resultado de análise |

**Endpoints:**
```
GET    /api/webhooks              # Listar webhooks
POST   /api/webhooks             # Criar webhook
DELETE /api/webhooks/{id}        # Remover webhook
POST   /api/webhooks/test        # Testar URL
POST   /api/webhooks/trigger/{event}  # Disparar manualmente
```

**Payload enviado:**
```json
{
  "event": "new_publication",
  "timestamp": "2026-04-20T14:00:00",
  "data": {
    "numero_processo": "0000832-56.2018.8.10.0001",
    "tribunal": "TJSP",
    "conteudo": "...",
    "captacao_nome": "Minhas Intimações"
  }
}
```

---

## 4. Métricas e Monitoramento

**Arquivos:** 
- `backend/djen/api/metrics.py`
- `backend/djen/api/routers/metrics.py`
- `backend/djen/api/advanced_logging.py`

**Endpoints:**
```
GET  /api/metrics             # Métricas JSON
GET  /api/metrics/prometheus # Formato Prometheus
GET  /api/metrics/health     # Health com métricas
POST /api/metrics/reset      # Resetar métricas
```

**Métricas coletadas:**
- Requests totais
- Tempo médio de resposta (ms)
- Percentis (p50, p95, p99)
- Taxa de erros
- Buscas por fonte
- Captações ativas
- Publicações hoje

---

## 5. Funcionalidades Opcionais

### 5.1 API Keys

**Arquivo:** `backend/djen/api/security.py`

```python
GET  /api/config/keys             # Listar keys
POST /api/config/keys             # Criar key
DELETE /api/config/keys/{id}      # Revogar key
```

### 5.2 2FA (TOTP)

```python
POST /api/config/2fa/generate    # Gerar QR code
POST /api/config/2fa/verify     # Verificar código
```

### 5.3 SSO/SAML (Opcional)

```python
GET  /api/config/sso            # Verificar status
POST /api/config/sso            # Configurar provider
```

### 5.4 Cache Redis (Opcional)

```python
GET  /api/config/cache/stats    # Estatísticas
POST /api/config/cache/clear     # Limpar cache
POST /api/config/cache/redis     # Conectar Redis
```

### 5.5 Backup Automático

```python
GET  /api/config/backup                    # Listar backups
POST /api/config/backup                   # Criar backup
POST /api/config/backup/{name}/restore     # Restaurar
POST /api/config/backup/auto/start         # Iniciar automático
POST /api/config/backup/auto/stop          # Parar automático
```

---

## 6. Endpoints Atualizados

### 6.1 Captacao - Novos endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/captacao/listar` | Listar com paginação e cache |
| GET | `/api/captacao/resumo` | Relatório discreto do sistema |

**Resposta paginada:**
```json
{
  "total": 350,
  "limit": 100,
  "offset": 0,
  "has_more": true,
  "next_offset": 100,
  "captacoes": [...]
}
```

---

## 7. Estrutura de Arquivos Nova

```
backend/djen/api/
├── app.py                          # FastAPI app + middleware de métricas
├── auth.py                        # JWT auth (com IS_PRODUCTION)
├── database.py                    # SQLite + webhook trigger
├── ratelimit.py                   # Rate Limiting (slowapi)
├── circuitbreaker.py              # Circuit Breaker
├── validation.py                  # Validação CNJ/OAB/Tribunais
├── webhook.py                     # Webhooks
├── metrics.py                     # Métricas
├── cache.py                       # Cache (Redis opcional)
├── backup.py                      # Backup automático
├── security.py                   # API Keys, 2FA, SSO
├── advanced_logging.py            # Log estruturado
└── routers/
    ├── captacao.py               # + cache, paginação
    ├── datajud.py                # + circuit breaker
    ├── validation.py             # NOVO
    ├── webhooks.py               # NOVO
    ├── metrics.py                 # NOVO
    └── advanced.py                # NOVO
```

---

## 8. Variáveis de Ambiente

### Novas variáveis

| Variável | Default | Descrição |
|----------|---------|-----------|
| `IS_PRODUCTION` | false | Obrigatório em produção |
| `JWT_SECRET_KEY` | — | Obrigatório se IS_PRODUCTION=true |

### Dependências novas (requirements.txt)

```
slowapi>=0.1.6          # Rate Limiting
redis>=4.0.0           # Cache (opcional)
```

---

## 9. Deploy

### Novo script de deploy

```bash
# Desenvolvimento
docker-compose up -d

# Produção
export IS_PRODUCTION=true
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker-compose up -d
```

---

## 10. Testes

### Testar Rate Limiting

```bash
# 6+ tentativas de login em 1 minuto
for i in {1..10}; do 
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8000/api/auth/login \
    -X POST -u "admin:admin"
done
```

Esperado: 5x `200`, depois `429`

### Testar Circuit Breaker

```bash
# 5 falhas consecutivas
for i in {1..10}; do 
  curl -s http://localhost:8000/api/datajud/buscar \
    -X POST -H "Content-Type: application/json" \
    -d '{"tribunal": "xxx"}'
done
```

Esperado: Após 5 falhas, retorna `503`

### Testar Validação

```bash
# Validar CNJ
curl -X POST "http://localhost:8000/api/validation/cnr?numero_processo=0000832-56.2018.8.10.0001"

# Listar tribunais
curl "http://localhost:8000/api/validation/tribunais"
```

---

## 11. Documentos Atualizados

| Documento | Status |
|-----------|--------|
| `TECNICO_PROGRAMADOR.md` | Complementar |
| `MAPEAMENTO_SISTEMA.md` | Manter existente |
| `GUIA_USUARIO.md` | Manter existente |
| `DOCS_DEPLOY.md` | Atualizado |

---

> Este documento deve ser lido em conjunto com os documentos originais do sistema.