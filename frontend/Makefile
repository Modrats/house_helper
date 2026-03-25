.PHONY: help install lint test format build dev deploy clean

# Default target
help:
	@echo "Frontend - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    Install dependencies"
	@echo ""
	@echo "Quality:"
	@echo "  make lint       Run ESLint"
	@echo "  make format     Auto-fix linting issues"
	@echo "  make test       Run unit tests (Vitest)"
	@echo ""
	@echo "Development:"
	@echo "  make dev        Start Vite dev server"
	@echo "  make build      Build for production"
	@echo "  make clean      Remove build artifacts"

# Install dependencies
install:
	pnpm install

# Lint TypeScript/React code
lint:
	pnpm exec eslint src --ext .ts,.tsx --max-warnings 0

# Auto-fix linting issues
format:
	pnpm exec eslint src --ext .ts,.tsx --fix

# Run unit tests
test:
	pnpm exec vitest run

# Start development server
dev:
	pnpm dev

# Build for production
build:
	pnpm build

# Deploy to Azure Static Web Apps (called from CI)
# Requires: SWA_NAME, SWA_RG
deploy: build
	az staticwebapp deploy \
		--name $(SWA_NAME) \
		--resource-group $(SWA_RG) \
		--app-location dist \
		--no-build

# Clean build artifacts
clean:
	rm -rf dist node_modules
