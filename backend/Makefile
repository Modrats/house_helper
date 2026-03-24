.PHONY: help install lint test format dev pipeline clean

# Default target
help:
	@echo "Backend - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    Install dependencies (using uv)"
	@echo ""
	@echo "Quality:"
	@echo "  make lint       Run Ruff linter and format checker"
	@echo "  make format     Auto-fix formatting issues"
	@echo "  make test       Run pytest"
	@echo ""
	@echo "Development:"
	@echo "  make dev        Start FastAPI dev server"
	@echo "  make pipeline   Run the filter pipeline"
	@echo "  make clean      Remove cache and build artifacts"

# Install dependencies using uv (reads pyproject.toml)
install:
	uv sync --all-extras

# Lint Python code (ruff for linting + formatting check)
lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

# Auto-fix formatting issues
format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

# Run tests
test:
	uv run pytest tests -v

# Start development server
dev:
	uv run uvicorn src.api.app:app --reload --port 8000

# Run filter pipeline against input_data houses
pipeline:
	uv run python -m src.run

# Clean artifacts
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache .venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
