.PHONY: help install dev test test-fast verify verify-quantum run lint format coverage clean docker-build docker-run

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
PORT ?= 5000

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	$(PIP) install -r requirements.txt

dev:  ## Install runtime and development dependencies
	$(PIP) install -r requirements-dev.txt

verify:  ## Check the environment, layout and datasets
	$(PYTHON) verify_requirements.py

verify-quantum:  ## Run the standalone algorithm verification
	$(PYTHON) verify_quantum.py

test:  ## Run the test suite with coverage
	$(PYTHON) -m pytest -q --cov --cov-report=term-missing

test-fast:  ## Run the test suite without coverage
	$(PYTHON) -m pytest -q

run:  ## Start the web application
	$(PYTHON) app.py

lint:  ## Lint the source
	$(PYTHON) -m ruff check .

format:  ## Format the source
	$(PYTHON) -m ruff format .

coverage:  ## Write an HTML coverage report
	$(PYTHON) -m pytest -q --cov --cov-report=html
	@echo "Open htmlcov/index.html"

check: verify verify-quantum test  ## Run every check

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

docker-build:  ## Build the container image
	docker build -t quantumhub .

docker-run:  ## Run the container image
	docker run --rm -p $(PORT):5000 quantumhub
