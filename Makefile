.PHONY: configure up down test lint smoke
configure:
	python3 infrastructure/scripts/configure.py
up: configure
	docker compose up --build -d --wait --wait-timeout 180
down:
	docker compose down
test:
	cd apps/api && uv run --frozen pytest -q
lint:
	cd apps/api && uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy
	cd apps/web && npm run lint && npm run typecheck
smoke:
	python3 infrastructure/scripts/smoke.py
