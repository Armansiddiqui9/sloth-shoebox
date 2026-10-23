.PHONY: install run seed test lint format check docker

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt

run:
	python -m sloth_shoebox

seed:
	python -m sloth_shoebox seed

test:
	python -m pytest

lint:
	ruff check . && ruff format --check .

format:
	ruff check --fix . && ruff format .

check: lint test

docker:
	docker build -t sloth-shoebox . && docker run --rm -p 8337:8337 -v sloth-data:/data sloth-shoebox
