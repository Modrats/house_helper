.PHONY: help install lint test format dev pipeline clean eval

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
	@echo "  make eval       Run all evaluators (set COMPONENT=name to run one)"

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

# Run all evaluators (set COMPONENT=name to run one)
eval:
ifdef COMPONENT
	uv run python -m src.evaluation.run_evals --component $(COMPONENT)
else
	uv run python -m src.evaluation.run_evals
endif

# Clean artifacts
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache .venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
