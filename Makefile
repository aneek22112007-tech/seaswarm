PY := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
COMPOSE := docker compose

.PHONY: up down test lint fmt migrate

up:
	@test -f .env || cp .env.example .env
	$(COMPOSE) up --build --wait

down:
	$(COMPOSE) down

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .
	$(PY) -m black --check .

fmt:
	$(PY) -m ruff check --fix .
	$(PY) -m black .

migrate:
	$(PY) -m alembic upgrade head
