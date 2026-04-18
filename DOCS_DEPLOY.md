# Guia de Deploy — CAPTAÇÃO BLINDADA v1.2.0

Este documento descreve o processo de deploy e a arquitetura do sistema **CAPTAÇÃO BLINDADA**, removendo dependências legadas do projeto anterior.

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

## 4. Verificação de Saúde
Após o deploy, valide através de:
- `https://captacao.jurislaw.com.br/api/health`
- Logs do backend: `docker compose logs -f backend`

---
> [!IMPORTANT]
> **Atenção**: O banco de dados SQLite local está em `/opt/CAPTAÇÃO BLINDADA/backend/djen/api/database.db`. Recomenda-se backup antes de grandes migrações.
