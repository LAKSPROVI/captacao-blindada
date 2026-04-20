# Guia de Deploy — CAPTAÇÃO BLINDADA v1.2.1

Este documento descreve o processo de deploy e a arquitetura do sistema **CAPTAÇÃO BLINDADA**, removendo dependências legadas do projeto anterior.

## ⚠️ IMPORTANTE - Variáveis Obrigatórias

### Variáveis Obrigatórias em Produção

Antes de iniciar em produção, você DEVE configurar:

```bash
# 1. Definir modo produção (OBRIGATÓRIO)
export IS_PRODUCTION=true

# 2. Gerar chave JWT segura (OBRIGATÓRIO)
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 3. Alterar senha admin (OBRIGATÓRIO)
export ADMIN_PASSWORD=sua-senha-forte-aqui
```

Se `IS_PRODUCTION=true` e `JWT_SECRET_KEY` não estiver configurada, o sistema **NÃO INICIARÁ**.

## 1. Arquitetura e Caminhos

O sistema opera de forma independente no servidor Contabo.

- **Domínio**: `https://captacao.jurislaw.com.br`
- **Diretório no Servidor**: `/opt/CAPTAÇÃO BLINDADA/`
- **Repositório Git**: `https://github.com/LAKSPROVI/captacao-blindada.git` (Folder: CAPTAÇÃO BLINDADA)

## 2. Processo de Deploy (Sincronização)

As alterações locais foram consolidadas. Para atualizar o servidor de produção, siga as instruções abaixo:

### Passo 1: Git Push (Local)
O código limpo e re-brandado já está pronto. Caso queira realizar o push manualmente:
```bash
git add .
git commit -m "feat: re-branding to CAPTAÇÃO BLINDADA and unified scheduling"
git push origin master
```

### Passo 2: Atualização no Servidor (Contabo)
Acesse via SSH e execute:
```bash
# Navegar para o diretório correto
cd "/opt/CAPTAÇÃO BLINDADA/"

# Puxar as atualizações
git pull origin master

# Re-build e Reinício (sem cache para garantir novos caminhos)
docker compose build --no-cache
docker compose up -d
```

## 3. O que mudou (v1.2.0)

- **Agendamento Unificado**: O Monitor e a Captação agora usam um motor granular de 10 minutos que respeita janelas horárias e intervalos individuais.
- **Brand Clean-up**: Todas as referências a sistemas antigos (CAPTAÇÃO BLINDADA) foram removidas dos scripts e arquivos de configuração.
- **Migração de Banco**: Ao subir, o sistema adiciona automaticamente as colunas `intervalo_minutos`, `horario_inicio`, `horario_fim`, `dias_semana` e `proxima_busca` à tabela `monitorados`.

## 4. Verificação de Saúde e Portas
Após o deploy, valide através de:
- **Domínio**: `https://captacao.jurislaw.com.br` (Internamente mapeado para a porta **8010**)
- **Health Check**: `https://captacao.jurislaw.com.br/api/health` (**Porta 8001**)
- Logs do backend: `docker compose logs -f backend`

## 5. Notas Importantes de Infraestrutura

- **Proxy Reverso (Nginx)**: O Nginx no host deve apontar seu `upstream` para `127.0.0.1:8010` para o frontend e `127.0.0.1:8001` para o backend.
- **Limite de Senha (Bcrypt)**: Devido a limitações da biblioteca `bcrypt`, a senha do administrador (`ADMIN_PASSWORD`) deve ter no máximo **72 bytes**. Senhas maiores serão truncadas automaticamente no sistema.
- **Banco de Dados**: O banco de dados SQLite oficial no container fica em `/app/data/captacao_blindada.db`. No host, ele é persistido no volume `captacao-data`.

---
> [!IMPORTANT]
> **Atenção**: O banco de dados SQLite local é centralizado. Para importar o conector em novos módulos, use sempre: `from djen.api.database import get_database`.
