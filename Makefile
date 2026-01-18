.PHONY: help install install-api install-ui run-api run-ui run-all test clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install both backend and frontend dependencies"
	@echo "  make run-api      - Run the FastAPI backend (localhost:8000)"
	@echo "  make run-ui       - Run the React frontend (localhost:5173)"
	@echo "  make test         - Run backend tests"
	@echo "  make clean        - Remove artifacts"

install: install-api install-ui

install-api:
	uv sync

install-ui:
	cd src/ui && bun install

run-api:
	uv run uvicorn src.api.main:app --reload

run-ui:
	cd src/ui && bun run dev

# Run both in parallel (requires make -j2 run-all)
run-all:
	@echo "Starting both services..."
	@$(MAKE) -j2 run-api run-ui

test:
	uv run pytest

clean:
	rm -rf .pytest_cache
	rm -rf **/__pycache__
