.PHONY: help install lint test format clean pre-commit install-hooks \
        install-backend install-frontend lint-backend lint-frontend \
        test-backend test-frontend format-backend format-frontend \
        dev-backend dev-frontend \
        docker-build docker-up docker-down backend-run frontend-run \
        deploy-backend deploy-frontend

ACR          ?= $(shell cd infra && terraform output -raw acr_login_server 2>/dev/null || echo "crhousehelperdev.azurecr.io")
IMAGE_TAG    ?= $(shell git rev-parse --short HEAD)
SWA_NAME     ?= $(shell cd infra && terraform output -raw swa_name 2>/dev/null || echo "stapp-househelper-dev")
SWA_RG       ?= $(shell cd infra && terraform output -raw resource_group_name 2>/dev/null || echo "rg-househelper-dev")
CA_NAME      ?= $(shell cd infra && terraform output -raw container_app_name 2>/dev/null || echo "ca-househelper-dev-backend")
CA_RG        ?= $(SWA_RG)

# Default target
help:
	@echo "House Helper - Development Commands"
	@echo ""
	@echo "Deploy:"
	@echo "  make deploy-backend   Build, tag (SHA + latest), push backend image to ACR"
	@echo "  make deploy-frontend  Build frontend and deploy to Azure Static Web App"
	@echo ""
	@echo "Setup:"
	@echo "  make install         Install all dependencies (backend + frontend)"
	@echo "  make install-hooks   Install git pre-commit/pre-push hooks"
	@echo ""
	@echo "Quality:"
	@echo "  make lint            Run all linters"
	@echo "  make test            Run all tests"
	@echo "  make format          Auto-fix formatting issues"
	@echo "  make pre-commit      Run pre-commit checks manually"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend     Start backend dev server"
	@echo "  make dev-frontend    Start frontend dev server"
	@echo "  make clean           Remove all build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    Build Docker images"
	@echo "  make docker-up       Start services (detached)"
	@echo "  make docker-down     Stop services"
	@echo "  make backend-run     Start only the backend container"
	@echo "  make frontend-run    Start only the frontend container"
	@echo ""
	@echo "Individual targets:"
	@echo "  make {lint,test,format}-{backend,frontend}"

#------------------------------------------------------------------------------
# Setup
#------------------------------------------------------------------------------

install: install-backend install-frontend install-hooks
	@echo "✅ All dependencies installed"

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd backend && $(MAKE) install

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && $(MAKE) install

install-hooks:
	@echo "🔧 Installing git hooks..."
	chmod +x scripts/*.sh
	./scripts/install-hooks.sh

#------------------------------------------------------------------------------
# Quality
#------------------------------------------------------------------------------

lint: lint-backend lint-frontend
	@echo "✅ All linting passed"

lint-backend:
	@echo "🐍 Linting backend..."
	cd backend && $(MAKE) lint

lint-frontend:
	@echo "⚛️  Linting frontend..."
	cd frontend && $(MAKE) lint

test: test-backend test-frontend
	@echo "✅ All tests passed"

test-backend:
	@echo "🧪 Testing backend..."
	cd backend && $(MAKE) test

test-frontend:
	@echo "🧪 Testing frontend..."
	cd frontend && $(MAKE) test

format: format-backend format-frontend
	@echo "✅ All code formatted"

format-backend:
	@echo "🐍 Formatting backend..."
	cd backend && $(MAKE) format

format-frontend:
	@echo "⚛️  Formatting frontend..."
	cd frontend && $(MAKE) format

pre-commit:
	@./scripts/pre-commit-wrapper.sh --all-files

#------------------------------------------------------------------------------
# Development
#------------------------------------------------------------------------------

dev-backend:
	cd backend && $(MAKE) dev

dev-frontend:
	cd frontend && $(MAKE) dev

#------------------------------------------------------------------------------
# Cleanup
#------------------------------------------------------------------------------

clean:
	cd backend && $(MAKE) clean
	cd frontend && $(MAKE) clean
	@echo "✅ Cleaned all artifacts"

#------------------------------------------------------------------------------
# Docker
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Deploy
#------------------------------------------------------------------------------

deploy-backend:
	@echo "🔐 Logging in to ACR..."
	az acr login --name $(shell echo $(ACR) | cut -d. -f1)
	@echo "🐳 Building backend image ($(ACR)/backend:$(IMAGE_TAG))..."
	docker build -t $(ACR)/backend:$(IMAGE_TAG) -t $(ACR)/backend:latest ./backend
	@echo "📤 Pushing $(ACR)/backend:$(IMAGE_TAG)..."
	docker push $(ACR)/backend:$(IMAGE_TAG)
	@echo "📤 Pushing $(ACR)/backend:latest..."
	docker push $(ACR)/backend:latest
	@echo "🚀 Updating Container App image..."
	az containerapp update \
		--name $(CA_NAME) \
		--resource-group $(CA_RG) \
		--image $(ACR)/backend:$(IMAGE_TAG)
	@echo "✅ Backend deployed: $(ACR)/backend:$(IMAGE_TAG)"

deploy-frontend:
	@echo "⚛️  Building frontend..."
	cd frontend && pnpm install --frozen-lockfile && pnpm build
	@echo "🔑 Fetching SWA deployment token..."
	$(eval SWA_TOKEN := $(shell az staticwebapp secrets list \
		--name $(SWA_NAME) \
		--resource-group $(SWA_RG) \
		--query properties.apiKey \
		--output tsv))
	@echo "📤 Deploying to $(SWA_NAME)..."
	npx --yes @azure/static-web-apps-cli deploy frontend/dist \
		--deployment-token $(SWA_TOKEN) \
		--env production
	@echo "✅ Frontend deployed to $(SWA_NAME)"

docker-build:
	@echo "🐳 Building Docker images..."
	docker compose build

docker-up:
	@echo "🐳 Starting services..."
	docker compose up -d

docker-down:
	@echo "🐳 Stopping services..."
	docker compose down

backend-run:
	@echo "🐳 Starting backend container..."
	docker compose up -d backend

frontend-run:
	@echo "🐳 Starting frontend container..."
	docker compose up -d frontend
