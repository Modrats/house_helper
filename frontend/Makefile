.PHONY: help install lint test build dev clean

# Default target
help:
	@echo "Frontend - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    Install dependencies"
	@echo ""
	@echo "Quality:"
	@echo "  make lint       Run ESLint"
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

# Run unit tests
test:
	pnpm exec vitest run

# Start development server
dev:
	pnpm dev

# Build for production
build:
	pnpm build

# Clean build artifacts
clean:
	rm -rf dist node_modules
