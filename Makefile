.PHONY: help install lint test format clean pre-commit install-hooks \
        install-backend install-frontend lint-backend lint-frontend \
        test-backend test-frontend format-backend format-frontend \
        dev dev-backend dev-frontend pipeline \
        docker-build docker-up docker-down backend-run frontend-run

# Default target
help:
	@echo "House Helper - Development Commands"
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
	@echo "  make dev             Start both dev servers (backend + frontend)"
	@echo "  make dev-backend     Start backend dev server"
	@echo "  make dev-frontend    Start frontend dev server"
	@echo "  make pipeline        Run the filter pipeline against input_data/"
	@echo "  make pipeline IMAGINEERING=1  Run pipeline with imagineering stage (costs money)"
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

dev:
	@echo "🚀 Starting dev servers (backend :8000 + frontend :5173)..."
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && $(MAKE) dev

dev-frontend:
	cd frontend && $(MAKE) dev

pipeline:
	@echo "🏗️  Running filter pipeline..."
	cd backend && $(MAKE) pipeline IMAGINEERING=$(IMAGINEERING)

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
