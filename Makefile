.PHONY: setup install hooks lint lint-fix format typecheck check test test-unit test-integration cov secrets build clean help

# ============================================================================
# Setup
# ============================================================================

setup: install hooks ## Full setup: install deps + git hooks
	@echo "Setup complete."

install: ## Install all dependencies
	uv sync

hooks: ## Install pre-commit hooks
	uv run pre-commit install

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run ruff linter
	uv run ruff check src/ tests/

lint-fix: ## Run ruff linter with auto-fix
	uv run ruff check --fix src/ tests/

format: ## Run ruff formatter + linter fix
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck: ## Run ty type checking (Astral)
	uv run ty check src/

check: lint typecheck secrets ## Lint + typecheck + leak-canary
	uv run ruff format --check src/ tests/

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	uv run pytest tests/ -v

test-unit: ## Run unit tests (skip integration)
	uv run pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests only (needs credentials)
	uv run pytest tests/ -v -m integration

cov: ## Run tests with 100% branch-coverage gate
	uv run pytest -m "not integration" --cov=src/hinge --cov-branch --cov-fail-under=100

secrets: ## Leak-canary: fail if reversal methodology leaked into tracked files
	uv run pytest tests/test_no_secrets.py -q

# ============================================================================
# Build
# ============================================================================

build: ## Build sdist + wheel and verify metadata + contents
	uv build
	uv run twine check dist/*
	@echo "--- wheel/sdist contents (must NOT contain reversal/, tests, secrets) ---"
	tar tzf dist/*.tar.gz

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/ .coverage

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
