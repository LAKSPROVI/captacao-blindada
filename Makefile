.PHONY: help install dev test lint build docker-build docker-up docker-down clean

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Backend ---

install: ## Instala dependencias do backend
	cd backend && pip install -r requirements.txt

install-dev: ## Instala dependencias de desenvolvimento
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

dev: ## Inicia backend em modo desenvolvimento
	cd backend && python -m uvicorn djen.api.app:app --host 0.0.0.0 --port 8000 --reload

test: ## Roda testes do backend
	cd backend && python -m pytest tests/ -v --tb=short

test-cov: ## Roda testes com cobertura
	cd backend && python -m pytest tests/ -v --cov=djen --cov-report=html

lint: ## Verifica estilo do codigo
	cd backend && python -m ruff check djen/

# --- Frontend ---

frontend-install: ## Instala dependencias do frontend
	cd frontend && npm install

frontend-dev: ## Inicia frontend em modo desenvolvimento
	cd frontend && npm run dev

frontend-build: ## Build de producao do frontend
	cd frontend && npm run build

# --- Docker ---

docker-build: ## Build das imagens Docker
	docker compose build

docker-up: ## Inicia containers
	docker compose up -d

docker-down: ## Para containers
	docker compose down

docker-logs: ## Ver logs dos containers
	docker compose logs -f

# --- Utils ---

clean: ## Limpa arquivos temporarios
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
	rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage
	rm -rf frontend/.next frontend/out

setup: install frontend-install ## Setup completo (backend + frontend)
	@echo "Setup completo! Use 'make dev' para iniciar o backend."
