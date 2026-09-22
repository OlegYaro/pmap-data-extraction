.PHONY: up down rebuild logs migrate create_migration downgrade psql lint check test test-db test-one fresh

# Pull in .env so the credentials live in one place and never reach the repo.
# Leading dash: don't fail on a fresh clone where .env doesn't exist yet.
-include .env
export

LOCAL_DB_URL = postgresql+asyncpg://extraction:extraction@localhost:5432/extraction
TEST_DB_NAME ?= extraction_test
TEST_DB_URL := $(dir $(DB_URL))$(TEST_DB_NAME)

up:
	docker compose up -d

down:
	docker compose down

rebuild:
	docker compose up -d --build

logs:
	docker compose logs -f

migrate:
	docker compose up migrate

create_migration:
	DB_URL=$(LOCAL_DB_URL) poetry run alembic revision --autogenerate -m "$(name)"

downgrade:
	poetry run alembic downgrade -1

psql:
	docker compose exec db psql -U extraction -d extraction

lint:
	poetry run ruff check --fix . && poetry run ruff format .

check:
	poetry run ruff check . && poetry run ruff format --check .

fresh:
	docker compose down -v
	docker compose up -d --build

test-db:
	@docker compose exec -T db psql -U extraction -tAc \
		"SELECT 1 FROM pg_database WHERE datname='$(TEST_DB_NAME)'" | grep -q 1 \
		|| docker compose exec -T db psql -U extraction -c "CREATE DATABASE $(TEST_DB_NAME)"

test: test-db
	DB_URL=$(TEST_DB_URL) poetry run alembic upgrade head
	DB_URL=$(TEST_DB_URL) poetry run pytest

test-one: test-db
	DB_URL=$(TEST_DB_URL) poetry run pytest -k "$(k)" -vv

load:
	DB_URL=$(LOCAL_DB_URL) poetry run python scripts/load_prg.py
