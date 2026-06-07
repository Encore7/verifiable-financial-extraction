# M0 verbs. Later milestones add: migrate, dev, seed-golden, eval.
.DEFAULT_GOAL := help
.PHONY: help install lint format fmt-check typecheck test check audit sast security build up infra-up infra-down infra-logs migrate revision clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Sync the locked environment (uv)
	uv sync

lint: ## Lint with ruff
	uv run ruff check .

format: ## Auto-format with ruff
	uv run ruff format .

fmt-check: ## Check formatting without writing (CI)
	uv run ruff format --check .

typecheck: ## Type-check with mypy
	uv run mypy

test: ## Run the test suite
	uv run pytest

check: lint fmt-check typecheck test ## Full local gate (matches CI)

audit: ## Scan dependencies for known vulnerabilities
	uv run pip-audit

sast: ## Static security analysis (bandit) over src
	uv run bandit -q -r src

security: audit sast ## All security checks

build: ## Build the api + worker images
	docker compose build

up: ## Start the full app (postgres + api + worker)
	docker compose up -d

infra-up: ## Start Postgres only
	docker compose up -d postgres

infra-down: ## Stop all services
	docker compose down

infra-logs: ## Tail Postgres logs
	docker compose logs -f postgres

migrate: ## Apply migrations (alembic upgrade head)
	uv run alembic upgrade head

revision: ## Autogenerate a migration: make revision m="message"
	uv run alembic revision --autogenerate -m "$(m)"

clean: ## Remove tooling caches
	rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov coverage.xml
