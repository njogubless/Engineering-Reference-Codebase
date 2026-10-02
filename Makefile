# Single entry point for running and verifying every stack.
# CI calls the same targets, so "green locally" means "green in CI".
#
#   make setup         install every stack's dependencies
#   make up            start Postgres, Redis, Mailpit (Docker)
#   make check         full quality gate: format, lint, types, tests, build
#   make check-<stack> one stack: django | fastapi | react | flutter | contract
#   make run-<stack>   run one app locally (migrates first)
#   make seed          demo users, posts and comments in both backends

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

PYTHON      ?= /usr/bin/python3
COMPOSE     := docker compose -f infrastructure/docker/compose.yaml
DJANGO_DIR  := django/reference_api
FASTAPI_DIR := fastapi/reference_api
REACT_DIR   := react/reference_app
FLUTTER_DIR := flutter/reference_app
CONTRACT_DIR:= tests/contract

DJANGO_ENV  := DJANGO_ENV_FILE=.env.test

.PHONY: help setup up down seed fuzz-contract check check-django check-fastapi check-react check-flutter check-contract \
        run-django run-fastapi run-react run-flutter

help:
	@grep -E '^#  ' Makefile | sed 's/^#  //'

# --- Setup ------------------------------------------------------------------

setup: setup-django setup-fastapi setup-react setup-flutter setup-contract

setup-django:
	cd $(DJANGO_DIR) && [ -d .venv ] || $(PYTHON) -m venv .venv
	cd $(DJANGO_DIR) && .venv/bin/pip install -q --require-hashes -r requirements.txt -r requirements-dev.txt

setup-fastapi:
	cd $(FASTAPI_DIR) && [ -d .venv ] || $(PYTHON) -m venv .venv
	cd $(FASTAPI_DIR) && .venv/bin/pip install -q --require-hashes -r requirements.txt -r requirements-dev.txt

setup-react:
	cd $(REACT_DIR) && pnpm install --frozen-lockfile

setup-flutter:
	cd $(FLUTTER_DIR) && flutter pub get

setup-contract:
	cd $(CONTRACT_DIR) && [ -d .venv ] || $(PYTHON) -m venv .venv
	cd $(CONTRACT_DIR) && .venv/bin/pip install -q --require-hashes -r requirements.txt

# --- Local services ---------------------------------------------------------

up:
	$(COMPOSE) up -d --wait

down:
	$(COMPOSE) down

# --- Quality gate -----------------------------------------------------------

check: check-django check-fastapi check-react check-flutter check-contract
	@echo "All quality gates passed."

check-django:
	cd $(DJANGO_DIR) && .venv/bin/ruff format --check .
	cd $(DJANGO_DIR) && .venv/bin/ruff check .
	cd $(DJANGO_DIR) && .venv/bin/mypy .
	cd $(DJANGO_DIR) && $(DJANGO_ENV) .venv/bin/python manage.py check --fail-level WARNING
	cd $(DJANGO_DIR) && $(DJANGO_ENV) .venv/bin/python manage.py makemigrations --check --dry-run
	cd $(DJANGO_DIR) && .venv/bin/pytest -q

FASTAPI_ENV := FASTAPI_ENV_FILE=.env.test

check-fastapi:
	cd $(FASTAPI_DIR) && .venv/bin/ruff format --check .
	cd $(FASTAPI_DIR) && .venv/bin/ruff check .
	cd $(FASTAPI_DIR) && .venv/bin/mypy .
	@# Migrations apply cleanly, and the models match them (no forgotten migration).
	cd $(FASTAPI_DIR) && $(FASTAPI_ENV) .venv/bin/python -m scripts.ensure_database
	cd $(FASTAPI_DIR) && $(FASTAPI_ENV) .venv/bin/alembic upgrade head
	cd $(FASTAPI_DIR) && $(FASTAPI_ENV) .venv/bin/alembic check
	cd $(FASTAPI_DIR) && .venv/bin/pytest -q

check-react:
	cd $(REACT_DIR) && pnpm format:check
	cd $(REACT_DIR) && pnpm lint
	cd $(REACT_DIR) && pnpm typecheck
	cd $(REACT_DIR) && pnpm test
	cd $(REACT_DIR) && pnpm build
	@# Generated API types must match the contract.
	cd $(REACT_DIR) && pnpm -s gen:api >/dev/null && git diff --exit-code -- src/lib/api/schema.d.ts

check-flutter:
	cd $(FLUTTER_DIR) && dart format --set-exit-if-changed .
	cd $(FLUTTER_DIR) && flutter analyze
	cd $(FLUTTER_DIR) && flutter test
	cd $(FLUTTER_DIR) && flutter build web --dart-define-from-file=config/development.json

check-contract:
	scripts/contract-check.sh

# Exploratory: fresh random inputs and more examples. Findings become
# regression tests; this target is not part of `make check`.
fuzz-contract:
	CONTRACT_FUZZ=1 scripts/contract-check.sh

# --- Demo data ----------------------------------------------------------------

seed:
	cd $(DJANGO_DIR) && .venv/bin/python manage.py seed_demo
	cd $(FASTAPI_DIR) && .venv/bin/python -m scripts.seed_demo

# --- Run --------------------------------------------------------------------

run-django:
	cd $(DJANGO_DIR) && .venv/bin/python manage.py migrate
	cd $(DJANGO_DIR) && .venv/bin/python manage.py runserver 8410

run-fastapi:
	cd $(FASTAPI_DIR) && .venv/bin/python -m scripts.ensure_database && .venv/bin/alembic upgrade head
	cd $(FASTAPI_DIR) && .venv/bin/uvicorn app.main:create_app --factory --port 8420 --reload

run-react:
	cd $(REACT_DIR) && pnpm dev --port 5410

run-flutter:
	cd $(FLUTTER_DIR) && flutter run -d chrome --web-port 5420 --dart-define-from-file=config/development.json
