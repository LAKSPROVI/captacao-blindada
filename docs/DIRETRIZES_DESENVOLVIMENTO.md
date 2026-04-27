# Diretrizes de Desenvolvimento — Captacao Peticao Blindada

> Versao: 3.0.0 | Atualizado: 2026-04-26 | Para: Desenvolvedores novos e existentes

---

## 1. Introducao

O **Captacao Peticao Blindada** e um sistema de captacao, monitoramento e analise inteligente de publicacoes judiciais. Ele lida com dados juridicos sensiveis e opera em arquitetura multi-tenant.

### Stack Tecnologico

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 15 + React 19 + TypeScript 5.7 + Tailwind CSS 3.4 |
| Backend | FastAPI + Uvicorn + Pydantic v2 + Python 3.11+ |
| Auth | PyJWT (HS256) + httpOnly cookies + bcrypt |
| Banco | SQLite WAL mode |
| Proxy | Caddy (TLS automatico) |
| Containers | Docker + Docker Compose |
| IA | 14 agentes em 6 camadas + LLM opcional |

### Documentacao Relacionada

| Documento | Conteudo |
|-----------|---------|
| `README.md` | Visao geral, setup, endpoints |
| `SECURITY.md` | Politica de seguranca completa |
| `DOCS_DEPLOY.md` | Guia de deploy |
| `docs/TECNICO_PROGRAMADOR.md` | Detalhes tecnicos |
| `docs/MAPEAMENTO_SISTEMA.md` | Mapeamento completo do sistema |
| `docs/GUIA_USUARIO.md` | Guia do usuario final |

---

## 2. Setup do Ambiente

### Pre-requisitos

- Python 3.11+
- Node.js 20+
- Docker e Docker Compose
- Git

### Setup Local

```bash
# Clonar
git clone https://github.com/LAKSPROVI/captacao-blindada.git
cd captacao-blindada

# Backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm ci
cd ..

# Configurar ambiente
cp .env.example .env
# Editar .env com suas credenciais (ver secao 6)
```

### Executar Localmente

```bash
# Backend (terminal 1)
cd backend
uvicorn djen.api.app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (terminal 2)
cd frontend
npm run dev
```

### Executar com Docker

```bash
docker compose up -d
# 3 containers: caddy, backend, frontend
```

---

## 3. Arquitetura

```
Internet → Caddy (:80/:443, TLS auto)
              ├── Frontend (Next.js, interno :3000)
              └── Backend (FastAPI, interno :8000)
                    ├── Auth (JWT httpOnly cookie)
                    ├── Tenant Isolation
                    ├── Rate Limiting
                    ├── 37+ Routers
                    ├── 14 Agentes IA (6 camadas)
                    ├── 7 Fontes de Dados
                    └── SQLite WAL (volume Docker)
```

### Multi-Tenant

Cada usuario pertence a um `tenant_id`. Todos os dados sao isolados por tenant. O role `master` pode acessar dados cross-tenant.

### Pipeline de Agentes IA

| Camada | Agentes | Funcao |
|--------|---------|--------|
| 1 | validador | Validacao CNJ |
| 2 | coletor_datajud, coletor_djen | Coleta paralela |
| 3 | extrator_entidades, analisador_movimentacoes, extrator_valores | Extracao |
| 4 | classificador_causa, analisador_cronologia, calculador_prazos | Analise |
| 5 | analisador_risco, analisador_jurisprudencia, validador_conformidade | Avancada |
| 6 | gerador_resumo, previsor_resultado | Consolidacao |

---

## 4. REGRAS DE SEGURANCA (OBRIGATORIO)

Esta e a secao mais importante deste documento. Violacoes destas regras podem expor dados de clientes.

### 4.1 NUNCA Fazer

| Regra | Motivo |
|-------|--------|
| NUNCA hardcodar credenciais no codigo | Exposicao em repositorio |
| NUNCA usar f-strings em SQL | SQL injection |
| NUNCA retornar `str(e)` em respostas HTTP | Vazamento de informacoes internas |
| NUNCA criar endpoints sem `Depends(get_current_user)` | Acesso nao autorizado |
| NUNCA fazer queries sem filtrar por `tenant_id` | Vazamento cross-tenant |
| NUNCA armazenar JWT em localStorage | Vulneravel a XSS |
| NUNCA desabilitar verificacao SSL (`verify=False`) | Man-in-the-middle |
| NUNCA rodar containers como root | Escalacao de privilegios |
| NUNCA commitar `.env` no git | Exposicao de credenciais |
| NUNCA usar `print()` em producao | Usar `logging` |
| NUNCA usar `python-jose` | Substituido por PyJWT |

### 4.2 SEMPRE Fazer

| Regra | Como |
|-------|------|
| SEMPRE adicionar `Depends(get_current_user)` | Em todo novo endpoint |
| SEMPRE filtrar por `tenant_id` | Em toda query ao banco |
| SEMPRE usar queries parametrizadas | `cursor.execute("... WHERE id = ?", (id,))` |
| SEMPRE sanitizar dados externos antes do LLM | Usar `sanitize.py` |
| SEMPRE validar output do LLM | Verificar tipos, tamanhos, enums |
| SEMPRE usar `log.error()` com `exc_info=True` | Para rastreabilidade |
| SEMPRE adicionar rate limiting | Em novos endpoints |
| SEMPRE usar validacao Pydantic | Nos schemas de entrada |
| SEMPRE testar com multiplos tenants | Para garantir isolamento |
| SEMPRE usar `os.environ.get()` para credenciais | Nunca valores default reais |

### 4.3 Padrao para Novos Endpoints

Todo novo endpoint DEVE seguir este padrao:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import get_current_user, require_role
from ..ratelimit import limiter

router = APIRouter(prefix="/api/meu-recurso", tags=["meu-recurso"])

# Schema de entrada com validacao
class MeuRecursoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(default="", max_length=1000)

@router.post("/")
@limiter.limit("30/minute")
async def criar_recurso(
    request: Request,
    dados: MeuRecursoCreate,
    user=Depends(get_current_user),  # OBRIGATORIO
):
    """Criar novo recurso."""
    try:
        db = get_database()
        # SEMPRE filtrar por tenant_id
        db.execute(
            "INSERT INTO meu_recurso (nome, descricao, tenant_id) VALUES (?, ?, ?)",
            (dados.nome, dados.descricao, user.get("tenant_id"))
        )
        return {"status": "ok", "message": "Recurso criado"}
    except Exception as e:
        log.error("Erro ao criar recurso", exc_info=True)
        # NUNCA retornar str(e) — mensagem generica
        raise HTTPException(status_code=500, detail="Erro interno ao criar recurso")
```

### 4.4 Padrao para Queries no Banco

```python
# CORRETO — parametrizado + tenant isolado
cursor.execute(
    "SELECT * FROM captacoes WHERE tenant_id = ? AND id = ?",
    (user["tenant_id"], captacao_id)
)

# CORRETO — verificar propriedade antes de alterar
row = cursor.execute(
    "SELECT tenant_id FROM captacoes WHERE id = ?", (captacao_id,)
).fetchone()
if not row or row["tenant_id"] != user["tenant_id"]:
    raise HTTPException(status_code=403, detail="Acesso negado")

# ERRADO — SQL injection via f-string
cursor.execute(f"SELECT * FROM captacoes WHERE id = {captacao_id}")

# ERRADO — sem filtro de tenant
cursor.execute("SELECT * FROM captacoes WHERE id = ?", (captacao_id,))
```

### 4.5 Padrao para Agentes de IA

```python
from djen.agents.sanitize import sanitize_for_llm, validate_llm_output

# 1. Sanitizar ANTES de enviar ao LLM
texto_limpo = sanitize_for_llm(texto_externo)

# 2. Montar prompt com dados sanitizados
prompt = f"Analise o seguinte texto juridico:\n{texto_limpo}"

# 3. Chamar LLM
resposta = await chamar_llm(prompt)

# 4. Validar output ANTES de armazenar
resultado_validado = validate_llm_output(resposta, tipo="resumo")
```

---

## 5. Estrutura de Diretorios

```
captacao-blindada/
├── backend/djen/
│   ├── api/
│   │   ├── app.py              # App principal + scheduler
│   │   ├── auth.py             # JWT + httpOnly cookies + RBAC
│   │   ├── crypto.py           # Criptografia Fernet para API keys
│   │   ├── database.py         # SQLite WAL (Singleton)
│   │   ├── ratelimit.py        # Rate limiting (slowapi)
│   │   ├── schemas.py          # Modelos Pydantic
│   │   └── routers/            # 37+ routers (todos com auth)
│   ├── agents/
│   │   ├── sanitize.py         # Sanitizacao anti-prompt-injection
│   │   ├── orchestrator.py     # Orquestrador de agentes
│   │   ├── specialized.py      # 14 agentes heuristicos
│   │   └── ml_agents.py        # Agentes LLM com fallback
│   ├── sources/                # 7 fontes de dados
│   └── settings.py             # Configuracoes (env vars)
├── frontend/src/
│   ├── app/                    # Paginas Next.js
│   ├── components/             # Componentes React
│   ├── hooks/                  # Custom hooks
│   └── lib/                    # API client + auth context
├── Caddyfile                   # Reverse proxy config
├── docker-compose.yml          # Orquestracao
├── .env.example                # Template de variaveis
└── docs/                       # Documentacao
```

### Onde adicionar novos recursos

| Tipo | Local |
|------|-------|
| Novo router/endpoint | `backend/djen/api/routers/` |
| Novo agente IA | `backend/djen/agents/` |
| Nova fonte de dados | `backend/djen/sources/` |
| Novo componente React | `frontend/src/components/` |
| Nova pagina | `frontend/src/app/` |
| Novo hook | `frontend/src/hooks/` |

---

## 6. Variaveis de Ambiente

### Obrigatorias

| Variavel | Descricao |
|----------|-----------|
| `JWT_SECRET_KEY` | Chave para assinar tokens JWT (min 32 chars) |
| `ENCRYPTION_KEY` | Chave para criptografia Fernet de API keys |
| `ADMIN_USERNAME` | Usuario administrador |
| `ADMIN_PASSWORD` | Senha do administrador (min 8 chars) |

### Fontes de Dados

| Variavel | Descricao |
|----------|-----------|
| `DATAJUD_API_KEY` | API key do DataJud (CNJ) |
| `DATAJUD_BASE_URL` | URL base do DataJud |
| `DJEN_API_BASE_URL` | URL base do DJEN |
| `BRIGHTDATA_PROXY_URL` | URL completa do proxy residencial |
| `BRIGHTDATA_API_KEY` | API key do Bright Data |
| `BRIGHTDATA_SCRAPING_BROWSER_WS` | WebSocket do Scraping Browser |

### Infraestrutura

| Variavel | Descricao |
|----------|-----------|
| `IS_PRODUCTION` | `true` em producao |
| `DOMAIN` | Dominio para TLS do Caddy |
| `ALLOWED_ORIGINS` | Origens CORS permitidas |
| `CAPTACAO_DB_PATH` | Caminho do banco SQLite |

### Opcionais

| Variavel | Descricao |
|----------|-----------|
| `GEMINI_API_KEY` | API key do Google Gemini |
| `LLM_API_URL` / `LLM_API_KEY` | Provedor LLM alternativo |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram |
| `WHATSAPP_TOKEN` | Token da API WhatsApp |
| `SMTP_*` | Configuracoes de email |

---

## 7. Banco de Dados

### SQLite com WAL Mode

- Thread-safe via `threading.local()` connections
- Singleton accessor: `from djen.api.database import get_database`
- Volume Docker: `/app/data/captacao_blindada.db`

### Adicionar Novas Tabelas

Novas tabelas DEVEM ser criadas em `database.py` no metodo `_init_schema()`:

```python
# Em database.py → _init_schema()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS minha_tabela (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        nome TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

NUNCA criar tabelas dentro de routers ou handlers de request.

---

## 8. Testes

```bash
# Rodar todos os testes
cd backend && python -m pytest -v

# Com cobertura
python -m pytest --cov=djen --cov-report=html

# Testes especificos
python -m pytest djen/tests/test_auth.py -v
```

### Checklist de Testes para Novas Features

- [ ] Endpoint retorna 401 sem autenticacao
- [ ] Endpoint retorna 403 para tenant errado
- [ ] Rate limiting funciona (429 apos limite)
- [ ] Validacao Pydantic rejeita dados invalidos
- [ ] Erros nao vazam detalhes internos
- [ ] Dados do LLM sao sanitizados

---

## 9. Deploy

```bash
# Conectar no servidor
ssh root@207.180.199.121

# Atualizar
cd "/opt/CAPTACAO BLINDADA/"
git pull origin master

# Rebuild
docker compose build --no-cache
docker compose up -d

# Verificar
docker compose ps  # 3 containers: caddy, backend, frontend
curl https://captacao.jurislaw.com.br/api/health
```

---

## 10. Convencoes de Codigo

### Python
- PEP 8 (formatador: ruff)
- Type hints em todas as funcoes
- Docstrings em funcoes publicas
- Logging em vez de print

### TypeScript
- Strict mode habilitado
- Sem `any` — usar tipos especificos
- Componentes funcionais com hooks

### Git
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Branch por feature: `feature/nome-da-feature`
- PR obrigatorio para merge em master

---

## 11. Checklist para Pull Requests

Antes de submeter um PR, verifique:

- [ ] Todos os endpoints tem `Depends(get_current_user)`
- [ ] Queries filtram por `tenant_id`
- [ ] Sem credenciais hardcoded no codigo
- [ ] Erros retornam mensagens genericas (sem `str(e)`)
- [ ] Rate limiting adicionado em novos endpoints
- [ ] Testes escritos e passando
- [ ] Schemas Pydantic validam entrada
- [ ] Dados externos sanitizados antes do LLM
- [ ] `.env.example` atualizado se nova variavel adicionada
- [ ] Documentacao atualizada se necessario

---

> Documento mantido pela equipe de desenvolvimento. Ultima revisao: 2026-04-26.
