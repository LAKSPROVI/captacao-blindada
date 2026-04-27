# Politica de Seguranca — Captacao Peticao Blindada

> Versao: 3.0.0 | Atualizado: 2026-04-26 | Para: Equipe tecnica, DevOps e auditoria

---

## 1. Visao Geral

O sistema **Captacao Peticao Blindada** lida com dados juridicos sensiveis (processos, partes, advogados, publicacoes). A seguranca segue o principio de **defesa em profundidade** com multiplas camadas:

- Autenticacao obrigatoria em todos os endpoints
- Isolamento multi-tenant em todas as queries
- Criptografia de dados sensiveis em repouso
- Rate limiting contra abuso
- Sanitizacao contra injecao (SQL, XSS, prompt injection)
- TLS automatico via Caddy
- Containers non-root com resource limits

---

## 2. Autenticacao e Autorizacao

### 2.1 JWT via httpOnly Cookies

| Aspecto | Implementacao |
|---------|--------------|
| Armazenamento | Cookie httpOnly (NAO localStorage) |
| Flags do cookie | `httpOnly=True`, `Secure=True`, `SameSite=Lax` |
| Algoritmo | HS256 (PyJWT) |
| Expiracao | 60 minutos |
| Login | `POST /api/auth/login` → define cookie |
| Logout | `POST /api/auth/logout` → limpa cookie |
| Refresh | `POST /api/auth/refresh` → novo cookie |
| Verificacao | `get_current_user()` verifica cookie primeiro, depois header Authorization |

**Por que httpOnly?** Tokens em localStorage sao vulneraveis a XSS — qualquer script malicioso pode roubar o token. Cookies httpOnly sao inacessiveis via JavaScript.

### 2.2 RBAC (Controle de Acesso por Roles)

| Role | Nivel | Acesso |
|------|-------|--------|
| `master` | Superadmin | Acesso total, cross-tenant |
| `admin` | Administrador | Gestao de usuarios e configuracoes |
| `tenant_admin` | Admin do tenant | Gestao dentro do proprio tenant |
| `editor` | Editor | CRUD de captacoes, monitores, processos |
| `viewer` | Visualizador | Somente leitura |

- Decorator `require_role()` protege endpoints por role
- Todos os 37+ routers exigem `Depends(get_current_user)`
- Unica excecao: `/api/health` (monitoramento)

### 2.3 Senhas

- Hash: bcrypt (limite de 72 bytes)
- Minimo: 8 caracteres (validacao Pydantic)
- Bloqueio: 5 tentativas falhadas = 5 minutos de lockout
- Limpeza automatica apos login bem-sucedido

---

## 3. Isolamento Multi-Tenant

Toda query ao banco de dados DEVE filtrar por `tenant_id`:

```python
# CORRETO
cursor.execute("SELECT * FROM captacoes WHERE tenant_id = ?", (user.tenant_id,))

# ERRADO — NUNCA fazer isso
cursor.execute("SELECT * FROM captacoes")
```

- Endpoints que acessam recursos por ID verificam se o `tenant_id` do recurso corresponde ao do usuario
- Retorna HTTP 403 se o tenant nao corresponder
- Role `master` pode acessar dados cross-tenant

---

## 4. Protecao de Dados

### 4.1 Criptografia de API Keys

| Aspecto | Implementacao |
|---------|--------------|
| Algoritmo | Fernet (AES-128-CBC + HMAC) |
| Arquivo | `backend/djen/api/crypto.py` |
| Chave | `ENCRYPTION_KEY` (variavel de ambiente) |
| Uso | API keys de IA criptografadas antes de salvar no SQLite |
| Fluxo | `salvar_ai_config` encripta → banco → `obter_ai_config` descriptografa |

### 4.2 Auditoria (Cadeia de Custodia)

- Todas as acoes registradas com integridade por hash chain
- SHA-256 encadeado para deteccao de adulteracao
- Campos: usuario, acao, entidade, timestamp, IP, hash anterior
- Endpoint: `/api/admin/auditoria`

---

## 5. Protecao contra Ataques

### 5.1 Rate Limiting

| Tipo de Endpoint | Limite |
|-----------------|--------|
| GET (leitura) | 60 req/min |
| POST/PUT/DELETE (escrita) | 30 req/min |
| Exports/Admin | 5 req/min |
| Login | 5 req/min |

- Implementado via `slowapi` com tracking por IP
- Headers de resposta: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`

### 5.2 CSRF

- Cookies httpOnly + `SameSite=Lax` previnem CSRF
- API tambem aceita Bearer token no header Authorization para clientes programaticos

### 5.3 XSS

- Content Security Policy (CSP) no frontend
- Scripts inline bloqueados
- JWT NAO armazenado em localStorage
- Headers: `X-XSS-Protection: 1; mode=block`

### 5.4 SQL Injection

- Todas as queries usam placeholders parametrizados (`?`)
- Nomes de colunas validados contra allowlists
- NUNCA usar f-strings para construir SQL

### 5.5 Prompt Injection (LLM)

| Aspecto | Implementacao |
|---------|--------------|
| Arquivo | `backend/djen/agents/sanitize.py` |
| Padroes filtrados | 15+ padroes de injecao |
| Exemplos | "ignore previous instructions", "system:", delimitadores |
| Validacao de output | Por tipo de agente (enums, scores, tamanhos) |

### 5.6 SSRF

- URLs de webhook validadas contra ranges de IP privados
- Protecao contra DNS rebinding recomendada

---

## 6. Infraestrutura

### 6.1 TLS/HTTPS

- **Caddy** como reverse proxy com TLS automatico (Let's Encrypt)
- HSTS habilitado: `max-age=63072000; includeSubDomains; preload`
- Apenas portas 80 (redirect) e 443 (HTTPS) expostas
- Backend e frontend acessiveis apenas via rede Docker interna

### 6.2 Docker

| Medida | Backend | Frontend |
|--------|---------|----------|
| Usuario | `USER 1000` | `USER node` |
| Imagem base | `python:3.11-slim-bookworm` | `node:20-alpine` |
| Resource limits | memory + CPU no compose | memory + CPU no compose |
| Security options | `no-new-privileges` | `no-new-privileges` |
| .dockerignore | Exclui `.env`, `.git`, `node_modules`, `__pycache__` | Idem |
| Logging | JSON com rotacao (10MB, 3 arquivos) | Idem |

### 6.3 Headers de Seguranca

| Header | Valor |
|--------|-------|
| Content-Security-Policy | `default-src 'self'; script-src 'self' 'unsafe-inline'; ...` |
| Strict-Transport-Security | `max-age=63072000; includeSubDomains; preload` |
| X-Frame-Options | `DENY` |
| X-Content-Type-Options | `nosniff` |
| X-XSS-Protection | `1; mode=block` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` |

---

## 7. Dependencias

- Todas as versoes pinadas com `==` (sem versoes flutuantes)
- `python-jose` substituido por `PyJWT[cryptography]==2.9.0` (mantido, sem CVEs)
- Pacotes npm pinados (sem prefixo `^`)
- `npm ci` em vez de `npm install` no Dockerfile

---

## 8. Variaveis de Ambiente Sensiveis

| Variavel | Obrigatoria | Descricao |
|----------|-------------|-----------|
| `JWT_SECRET_KEY` | SIM | App recusa iniciar sem ela |
| `ENCRYPTION_KEY` | SIM | Criptografia de API keys no banco |
| `ADMIN_PASSWORD` | SIM | Sem valor padrao — deve ser definida |
| `DATAJUD_API_KEY` | Nao | API key do DataJud (CNJ) |
| `BRIGHTDATA_*` | Nao | Credenciais do proxy Bright Data |
| `DOMAIN` | Producao | Dominio para TLS do Caddy |

- `.env` esta no `.gitignore` — NUNCA commitar
- `.env.example` contem template sem valores reais

---

## 9. Reporte de Vulnerabilidades

Se voce encontrar uma vulnerabilidade de seguranca:

1. **NAO** abra uma issue publica
2. Envie um email para a equipe de desenvolvimento com:
   - Descricao da vulnerabilidade
   - Passos para reproduzir
   - Impacto potencial
3. Aguarde confirmacao antes de divulgar publicamente

Prazo de resposta: 48 horas uteis.

---

> Documento mantido pela equipe de desenvolvimento. Ultima revisao: 2026-04-26.
