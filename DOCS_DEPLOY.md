# Guia de Deploy — CAPTACAO BLINDADA v3.0.0

Este documento descreve o processo completo de deploy, arquitetura, segurança e manutenção do sistema **CAPTAÇÃO BLINDADA v3.0.0** em produção, utilizando **Caddy** como reverse proxy com TLS automático.

---

## 1. Pré-requisitos

- Servidor: **Contabo VPS**
- Domínio: `captacao.jurislaw.com.br` (DNS apontando para o IP do VPS)
- Docker e Docker Compose instalados
- Git instalado
- Portas **80** e **443** liberadas no firewall
- Acesso SSH ao servidor

---

## 2. Variáveis de Ambiente Obrigatórias

Crie o arquivo `.env` na raiz do projeto. **Todas** as variáveis abaixo são obrigatórias em produção.

```bash
# ============================================
# SEGURANÇA — OBRIGATÓRIO
# ============================================

# Chave secreta para assinatura de tokens JWT
# Gere com: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=

# Chave de criptografia para API keys armazenadas no banco de dados
# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=

# ============================================
# CREDENCIAIS DO ADMINISTRADOR — OBRIGATÓRIO
# ============================================

# Nome de usuário do administrador do sistema
ADMIN_USERNAME=

# Senha do administrador — NÃO use senhas fracas
# Limite de 72 bytes (limitação do bcrypt)
ADMIN_PASSWORD=

# ============================================
# APIs EXTERNAS — OBRIGATÓRIO
# ============================================

# Chave de acesso à API do DataJud (CNJ)
DATAJUD_API_KEY=

# ============================================
# PROXY BRIGHTDATA — OBRIGATÓRIO
# ============================================

# Host do proxy BrightData
BRIGHTDATA_HOST=

# Porta do proxy BrightData
BRIGHTDATA_PORT=

# Usuário de autenticação do BrightData
BRIGHTDATA_USERNAME=

# Senha de autenticação do BrightData
BRIGHTDATA_PASSWORD=

# ============================================
# REDE / DOMÍNIO — OBRIGATÓRIO
# ============================================

# Domínio público — usado pelo Caddy para provisionar certificado TLS via Let's Encrypt
DOMAIN=captacao.jurislaw.com.br

# Origens permitidas para CORS (separadas por vírgula)
ALLOWED_ORIGINS=https://captacao.jurislaw.com.br

# ============================================
# MODO DE EXECUÇÃO
# ============================================
IS_PRODUCTION=true
```

> **ATENÇÃO**: Com `IS_PRODUCTION=true`, o sistema **recusa iniciar** se `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_USERNAME` ou `ADMIN_PASSWORD` não estiverem definidas.

---

## 3. Arquitetura

O sistema roda em **3 containers** Docker orquestrados via Docker Compose:

```
Internet (HTTPS)
       │
       ▼
┌─────────────────────────────────┐
│  Caddy (reverse proxy)          │
│  Portas expostas: 80 / 443      │
│  TLS automático (Let's Encrypt) │
└───────┬──────────────┬──────────┘
        │              │
        ▼              ▼
  ┌──────────┐   ┌──────────┐
  │ Frontend  │   │ Backend  │
  │ (interno) │   │ (interno)│
  └──────────┘   └────┬─────┘
                      │
                      ▼
                ┌──────────┐
                │  SQLite   │
                │  (volume) │
                └──────────┘
```

| Componente | Descrição |
|---|---|
| **caddy** | Reverse proxy com TLS automático via Let's Encrypt. Única porta exposta ao mundo: 80 e 443. |
| **backend** | API FastAPI. Rede interna apenas — sem portas expostas ao host. |
| **frontend** | Aplicação web. Rede interna apenas — sem portas expostas ao host. |

Detalhes da infraestrutura:

- **Reverse Proxy**: Caddy (substitui o Nginx das versões anteriores)
- **TLS**: Provisionamento e renovação automática via Let's Encrypt — zero configuração manual de certificados
- **Portas expostas**: Apenas `80` (redirect para HTTPS) e `443` (Caddy)
- **Backend e Frontend**: Acessíveis somente via rede interna do Docker
- **Servidor**: Contabo VPS
- **Domínio**: `captacao.jurislaw.com.br`
- **Diretório no servidor**: `/opt/CAPTAÇÃO BLINDADA/`
- **Repositório**: `https://github.com/LAKSPROVI/captacao-blindada.git`
- **Banco de dados**: SQLite persistido em volume Docker `captacao-data`

---

## 4. Processo de Deploy

### 4.1 Primeiro deploy

```bash
# Conectar ao servidor via SSH
ssh usuario@<IP_DO_SERVIDOR>

# Navegar até o diretório do projeto
cd "/opt/CAPTAÇÃO BLINDADA/"

# Clonar o repositório (apenas na primeira vez)
git clone https://github.com/LAKSPROVI/captacao-blindada.git .

# Criar e configurar o arquivo .env com TODAS as variáveis obrigatórias
cp .env.example .env
nano .env

# Build sem cache e start dos containers
docker compose build --no-cache
docker compose up -d

# Verificar se os 3 containers estão rodando
docker compose ps
```

### 4.2 Atualizações (deploys subsequentes)

```bash
cd "/opt/CAPTAÇÃO BLINDADA/"

# Puxar as atualizações do repositório
git pull origin master

# Configurar novas variáveis de ambiente, se houver
nano .env

# Rebuild completo sem cache
docker compose build --no-cache

# Subir os containers atualizados
docker compose up -d

# Verificar status
docker compose ps

# Acompanhar logs em tempo real (opcional)
docker compose logs -f
```

### 4.3 Rollback rápido

```bash
# Listar commits recentes
git log --oneline -5

# Voltar para o commit desejado
git checkout <commit-hash>

# Rebuild e restart
docker compose build --no-cache
docker compose up -d
```

---

## 5. Certificado TLS (Automático)

O Caddy provisiona e renova certificados TLS automaticamente via **Let's Encrypt**:

- Na primeira requisição ao domínio, o Caddy obtém o certificado automaticamente
- A renovação acontece antes da expiração, sem intervenção manual
- Não é necessário configurar certbot, cron jobs ou qualquer gerenciamento manual de certificados
- Os certificados ficam armazenados no volume Docker `caddy_data`

**Requisitos para o TLS funcionar:**
1. O DNS de `captacao.jurislaw.com.br` deve apontar para o IP do servidor
2. As portas 80 e 443 devem estar abertas no firewall
3. A variável `DOMAIN` deve estar corretamente configurada no `.env`

---

## 6. Verificação Pós-Deploy (Health Check)

Após o deploy, valide o funcionamento do sistema:

| Verificação | URL / Comando |
|---|---|
| Health Check da API | `https://captacao.jurislaw.com.br/api/health` |
| Frontend | `https://captacao.jurislaw.com.br` |
| Certificado TLS | Verificar cadeado no navegador (emitido por Let's Encrypt) |
| Status dos containers | `docker compose ps` |
| Logs do backend | `docker compose logs -f backend` |
| Logs do frontend | `docker compose logs -f frontend` |
| Logs do Caddy | `docker compose logs -f caddy` |

Exemplo de health check via terminal:

```bash
curl -s https://captacao.jurislaw.com.br/api/health
# Resposta esperada: {"status": "healthy", ...}
```

---

## 7. Segurança

A v3.0.0 implementa múltiplas camadas de segurança:

### Autenticação e autorização
- **Todos os endpoints da API requerem autenticação** via token JWT
- Tokens JWT assinados com `JWT_SECRET_KEY` exclusiva do ambiente de produção
- Sessões com expiração configurável

### Proteção de dados
- **API keys criptografadas** no banco de dados com `ENCRYPTION_KEY` (Fernet/AES)
- Senhas armazenadas com hash bcrypt (custo computacional elevado)
- Variáveis sensíveis nunca expostas em logs ou respostas da API

### Rate limiting
- Limitação de requisições por IP para prevenir abuso e ataques de força bruta
- Configurado no backend para todos os endpoints públicos

### Segurança dos containers
- **Non-root**: Todos os containers executam como usuário não-root
- **no-new-privileges**: Impede escalação de privilégios dentro dos containers
- **Read-only filesystem**: Sistema de arquivos somente leitura onde possível
- **Resource limits**: Limites de CPU e memória configurados no `docker-compose.yml`
- **Log rotation**: Rotação automática de logs para evitar consumo excessivo de disco

```yaml
# Configuração de segurança aplicada nos services
security_opt:
  - no-new-privileges:true
read_only: true
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### CORS
- Origens permitidas controladas pela variável `ALLOWED_ORIGINS`
- Em produção, apenas `https://captacao.jurislaw.com.br` é permitido

---

## 8. Backup

### Banco de dados (SQLite)

```bash
# Backup manual
docker compose exec backend sqlite3 /app/data/captacao_blindada.db ".backup '/app/data/backup.db'"
docker cp $(docker compose ps -q backend):/app/data/backup.db ./backup_$(date +%Y%m%d).db
```

**Recomendação**: Configure um cron job para backup diário:

```bash
# Adicionar ao crontab (crontab -e)
0 3 * * * cd "/opt/CAPTAÇÃO BLINDADA/" && docker compose exec -T backend sqlite3 /app/data/captacao_blindada.db ".backup '/app/data/backup.db'" && docker cp $(docker compose ps -q backend):/app/data/backup.db /opt/backups/captacao_$(date +\%Y\%m\%d).db
```

### Volumes do Caddy

Os certificados TLS ficam no volume `caddy_data`. Backup opcional (evita re-emissão):

```bash
docker run --rm -v caddy_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/caddy_data_$(date +%Y%m%d).tar.gz /data
```

---

## 9. Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados de cada container
docker compose logs backend
docker compose logs frontend
docker compose logs caddy

# Verificar se as variáveis de ambiente estão corretas
docker compose config
```

**Causa mais comum**: Variáveis obrigatórias ausentes ou vazias no `.env`. O backend recusa iniciar sem `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_USERNAME` e `ADMIN_PASSWORD`.

---

### Caddy não obtém certificado TLS

```bash
# Verificar logs do Caddy relacionados a TLS
docker compose logs caddy | grep -i "tls\|acme\|certificate"
```

**Causas comuns:**
- DNS de `captacao.jurislaw.com.br` não aponta para o IP do servidor
- Portas 80 e/ou 443 bloqueadas no firewall do VPS
- Rate limit do Let's Encrypt atingido (máx. 5 certificados duplicados por semana)

**Solução:**

```bash
# Verificar resolução DNS
dig captacao.jurislaw.com.br

# Verificar se as portas estão abertas
ss -tlnp | grep -E ':80|:443'

# Liberar portas no firewall (se necessário)
ufw allow 80/tcp
ufw allow 443/tcp
```

---

### Erro 502 Bad Gateway

O Caddy não consegue alcançar o backend ou frontend na rede interna.

```bash
# Verificar se todos os containers estão na mesma rede Docker
docker network ls
docker network inspect captacao_default

# Testar conectividade interna do backend
docker compose exec backend curl -s http://localhost:8001/api/health

# Verificar se o backend está ouvindo na porta correta
docker compose exec backend ss -tlnp
```

---

### Health check retorna erro

```bash
# Testar diretamente no container do backend
docker compose exec backend curl -s http://localhost:8001/api/health

# Verificar logs do backend para erros
docker compose logs --tail=50 backend
```

**Causas comuns:**
- Banco de dados SQLite corrompido ou inacessível
- Variáveis de ambiente inválidas
- Dependência externa (DataJud, BrightData) indisponível

---

### Banco de dados corrompido

```bash
# Verificar integridade do SQLite
docker compose exec backend sqlite3 /app/data/captacao_blindada.db "PRAGMA integrity_check;"

# Restaurar a partir de backup
docker cp ./backup_YYYYMMDD.db $(docker compose ps -q backend):/app/data/captacao_blindada.db
docker compose restart backend
```

---

### Consumo excessivo de disco

```bash
# Ver uso de disco pelos containers e volumes
docker system df -v

# Limpar imagens e containers não utilizados
docker system prune -f

# CUIDADO: remove volumes não utilizados também
docker system prune --volumes -f
```

---

### Reiniciar tudo do zero

```bash
cd "/opt/CAPTAÇÃO BLINDADA/"

# Parar e remover todos os containers
docker compose down

# Rebuild completo sem cache
docker compose build --no-cache

# Subir novamente
docker compose up -d

# Verificar
docker compose ps
docker compose logs -f
```

---

### Problemas com proxy BrightData

```bash
# Verificar se as credenciais estão configuradas
docker compose exec backend env | grep BRIGHTDATA

# Testar conectividade com o proxy (dentro do container)
docker compose exec backend curl -x http://$BRIGHTDATA_USERNAME:$BRIGHTDATA_PASSWORD@$BRIGHTDATA_HOST:$BRIGHTDATA_PORT -s https://httpbin.org/ip
```

---

## 10. Comandos Úteis

```bash
# Ver status de todos os containers
docker compose ps

# Acompanhar logs em tempo real (todos os containers)
docker compose logs -f

# Acompanhar logs de um container específico
docker compose logs -f backend

# Reiniciar apenas o backend
docker compose restart backend

# Parar tudo
docker compose down

# Rebuild e restart de um container específico
docker compose build --no-cache backend
docker compose up -d backend

# Acessar shell do container backend
docker compose exec backend sh

# Ver configuração resolvida do Docker Compose
docker compose config
```

---

> **Nota**: Este guia é para a versão **v3.0.0** com Caddy como reverse proxy. Para versões anteriores que utilizavam Nginx, consulte o histórico do repositório Git.
