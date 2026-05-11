.PHONY: setup install hooks lint lint-fix format typecheck pre-commit test test-unit test-integration db-reset db-migrate db-upgrade clean help

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

typecheck: ## Run mypy type checking
	uv run mypy src/

pre-commit: ## Run all pre-commit hooks on all files
	uv run pre-commit run --all-files

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	uv run pytest tests/ -v

test-unit: ## Run unit tests (skip integration)
	uv run pytest tests/ -v -m "not integration"

test-integration: ## Run integration tests only
	uv run pytest tests/ -v -m integration

# ============================================================================
# Database
# ============================================================================

db-reset: ## Delete local SQLite database
	rm -f hinge.db
	@echo "Database reset."

db-migrate: ## Generate a new Alembic migration (usage: make db-migrate msg="add foo")
	uv run alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply pending Alembic migrations
	uv run alembic upgrade head

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
