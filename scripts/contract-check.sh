#!/usr/bin/env bash
# Verifies both backends against contracts/openapi.yaml:
#   1. lints the contract (Spectral)
#   2. starts Django (:8411) and FastAPI (:8421) against the test databases
#   3. runs tests/contract (operation drift, Schemathesis conformance, Problem shapes)
# Needs `make up` (Postgres + Redis) and `make setup`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DJANGO_PORT=8411
FASTAPI_PORT=8421
PIDS=()

cleanup() {
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT

echo "→ Linting contract"
npx --yes @stoplight/spectral-cli@6 lint "$ROOT/contracts/openapi.yaml" \
  --ruleset "$ROOT/contracts/.spectral.yaml" --fail-severity=warn

# Throwaway databases: Schemathesis creates random data, which must never
# land in a development database.
PG="postgresql://reference:reference@localhost:5433"
for db in django_contract fastapi_contract; do
  psql "$PG/postgres" -q -c "DROP DATABASE IF EXISTS $db" -c "CREATE DATABASE $db"
done
export DJANGO_DATABASE_URL="$PG/django_contract"
export FASTAPI_DATABASE_URL="$PG/fastapi_contract"

echo "→ Migrating"
(cd "$ROOT/django/reference_api" && DJANGO_ENV_FILE=.env.test DATABASE_URL="$DJANGO_DATABASE_URL" \
  .venv/bin/python manage.py migrate -v0)
(cd "$ROOT/fastapi/reference_api" && FASTAPI_ENV_FILE=.env.test DATABASE_URL="$FASTAPI_DATABASE_URL" \
  .venv/bin/alembic upgrade head >/dev/null 2>&1)

echo "→ Starting Django on :$DJANGO_PORT"
# `exec` replaces the subshell with the server, so `$!` is the server's PID and
# the cleanup trap really stops it (without exec, only the subshell is killed).
(cd "$ROOT/django/reference_api" && DJANGO_ENV_FILE=.env.test DATABASE_URL="$DJANGO_DATABASE_URL" \
  exec .venv/bin/python manage.py runserver "$DJANGO_PORT" --noreload >/tmp/contract-django.log 2>&1) &
PIDS+=($!)

echo "→ Starting FastAPI on :$FASTAPI_PORT"
(cd "$ROOT/fastapi/reference_api" && FASTAPI_ENV_FILE=.env.test DATABASE_URL="$FASTAPI_DATABASE_URL" \
  exec .venv/bin/uvicorn app.main:create_app --factory --port "$FASTAPI_PORT" >/tmp/contract-fastapi.log 2>&1) &
PIDS+=($!)

wait_for() {
  for _ in $(seq 1 50); do
    curl -fs "$1/health/live" >/dev/null && return 0
    sleep 0.2
  done
  echo "Server at $1 did not start; see /tmp/contract-*.log" >&2
  return 1
}
wait_for "http://localhost:$DJANGO_PORT"
wait_for "http://localhost:$FASTAPI_PORT"

echo "→ Running contract tests"
cd "$ROOT/tests/contract"
DJANGO_BASE_URL="http://localhost:$DJANGO_PORT" FASTAPI_BASE_URL="http://localhost:$FASTAPI_PORT" \
  .venv/bin/pytest -q "$@"
