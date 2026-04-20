#!/bin/bash
# =============================================================================
# CAPTAÇÃO BLINDADA - Deploy Produção
# =============================================================================
# Execute: bash deploy-prod.sh
# =============================================================================

set -e

echo "================================================"
echo "CAPTAÇÃO BLINDADA - DEPLOY PRODUÇÃO"
echo "================================================"

# --- Cores ---
VERDE='\033[0;32m'
VERMELHO='\033[0;31m'
AZUL='\033[0;34m'
AMARELO='\033[1;33m'
SEMCOR='\033[0m'

# --- Verificar variáveis obrigatórias ---
echo -e "${AZUL}[1/4]${SEMCOR} Verificando configurações..."

if [ -z "$JWT_SECRET_KEY" ]; then
    echo -e "${VERMELHO}[ERRO]${SEMCOR} JWT_SECRET_KEY não está definida!"
    echo "Defina a variável: export JWT_SECRET_KEY=\$(python -c \"import secrets; print(secrets.token_hex(32))\")"
    exit 1
fi

KEY_LEN=${#JWT_SECRET_KEY}
if [ $KEY_LEN -lt 32 ]; then
    echo -e "${VERMELHO}[ERRO]${SEMCOR} JWT_SECRET_KEY muito curta! Mínimo 32 caracteres."
    exit 1
fi

echo -e "${VERDE}[OK]${SEMCOR} JWT_SECRET_KEY configurada ($KEY_LEN caracteres)"

# --- Atualizar .env ---
echo -e "${AZUL}[2/4]${SEMCOR} Atualizando .env..."

cat > .env << EOF
# =============================================================================
# CAPTAÇÃO BLINDADA - PRODUÇÃO
# =============================================================================
IS_PRODUCTION=true
JWT_SECRET_KEY=$JWT_SECRET_KEY
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD
CAPTACAO_DB_PATH=/app/data/captacao_blindada.db
EOF

echo -e "${VERDE}[OK]${SEMCOR} .env atualizado"

# --- Deploy ---
echo -e "${AZUL}[3/4]${SEMCOR} Executando deploy..."

# Parar
docker-compose down --remove-orphans 2>/dev/null || true

# Build
docker-compose build --no-cache backend

# Start
docker-compose up -d

# --- Verificar ---
echo -e "${AZUL}[4/4]${SEMCOR} Verificando..."

sleep 15

# Check logs
LOGS=$(docker-compose logs backend --tail=20 2>/dev/null)
if echo "$LOGS" | grep -qi "error\|fatal\|exception"; then
    echo -e "${VERMELHO}[ERRO]${SEMCOR} Erros detectados no log!"
    docker-compose logs backend --tail=50
    exit 1
fi

# Check health
MAX_TRIES=5
for i in $(seq 1 $MAX_TRIES); do
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null || echo "000")
    if [ "$HEALTH" = "200" ]; then
        echo -e "${VERDE}[OK]${SEMCOR} API Respondendo!"
        break
    else
        echo "Aguardando inicialização... ($i/$MAX_TRIES)"
        sleep 5
    fi
done

# --- Resultado ---
echo ""
echo "================================================"
echo "DEPLOY PRODUÇÃO CONCLUÍDO!"
echo "================================================"
echo ""
echo "URLs:"
echo "  API:        https://captacao.jurislaw.com.br"
echo "  Docs:       https://captacao.jurislaw.com.br/docs"
echo ""
echo "Credenciais:"
echo "  Usuário: admin"
echo "  Senha: (configurada)"
echo ""
echo "Comandos úteis:"
echo "  docker-compose logs -f backend"
echo "  docker-compose restart backend"
echo ""