#!/bin/bash
# =============================================================================
# CAPTAÇÃO BLINDADA - Script de Deploy
# =============================================================================
# Execute no servidor: bash deploy.sh
# =============================================================================

set -e

echo "================================================"
echo "CAPTAÇÃO BLINDADA - DEPLOY v1.2.1"
echo "================================================"

# --- Verificar Docker ---
if ! command -v docker &> /dev/null; then
    echo "ERRO: Docker não encontrado. Instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERRO: docker-compose não encontrado."
    exit 1
fi

# --- Cores para output ---
VERDE='\033[0;32m'
AZUL='\033[0;34m'
AMARELO='\033[1;33m'
SEMCOR='\033[0m'

echo -e "${AZUL}[1/5]${SEMCOR} Verificando configuração..."

# --- Verificar .env ---
if [ ! -f ".env" ]; then
    echo -e "${AMARELO}[AVISO]${SEMCOR} Arquivo .env não encontrado. Criando..."
    cp .env.example .env
fi

# --- Verificar variáveis de produção ---
IS_PROD=$(grep "^IS_PRODUCTION=" .env | cut -d'=' -f2)
JWT_KEY=$(grep "^JWT_SECRET_KEY=" .env | cut -d'=' -f2)

if [ "$IS_PROD" = "true" ] && [ -z "$JWT_KEY" ]; then
    echo -e "${AMARELO}[ERRO]${SEMCOR} IS_PRODUCTION=true mas JWT_SECRET_KEY não está configurado!"
    echo "Configure JWT_SECRET_KEY no arquivo .env"
    exit 1
fi

echo -e "${VERDE}[OK]${SEMCOR} Configuração verificada"

# --- Parar serviços existentes ---
echo -e "${AZUL}[2/5]${SEMCOR} Parando serviços existentes..."
docker-compose down --remove-orphans 2>/dev/null || true

# --- build imagens ---
echo -e "${AZUL}[3/5]${SEMCOR} Construindo imagens Docker..."
docker-compose build --no-cache

# --- Iniciar serviços ---
echo -e "${AZUL}[4/5]${SEMCOR} Iniciando serviços..."
docker-compose up -d

# --- Aguardar backend ---
echo -e "${AZUL}[5/5]${SEMCOR} Verificando saúde..."
sleep 10

# --- Verificar status ---
echo ""
echo "================================================"
echo "STATUS DOS SERVIÇOS"
echo "================================================"
docker-compose ps

# --- Teste de health ---
echo ""
echo "Testando Health Check..."
HEALTH=$(curl -s http://localhost:8000/api/health 2>/dev/null || echo "erro")

if echo "$HEALTH" | grep -q "success"; then
    echo -e "${VERDE}[OK]${SEMCOR} Backend Healthy!"
    echo "API: http://localhost:8000"
    echo "Docs: http://localhost:8000/docs"
else
    echo -e "${AMARELO}[AVISO]${SEMCOR} Backend pode ainda estar inicializando"
    echo "Verifique com: docker-compose logs backend"
fi

echo ""
echo "================================================"
echo "DEPLOY CONCLUÍDO!"
echo "================================================"
echo ""
echo "Próximos passos:"
echo "  - Acesse: http://localhost:8000/docs"
echo "  - Login: admin / (senha do .env)"
echo "  - Logs: docker-compose logs -f"
echo ""