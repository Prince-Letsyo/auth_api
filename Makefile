# --- Configuration Variables ---
PACKAGE_MANAGER := uv
# File containing your main dependencies
REQUIREMENTS := requirements.txt


# --- Phony Targets (Commands that don't produce a file) ---
.PHONY: help install install-dev serve test lint format clean

# --- Default Target ---
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- Environment Setup ---
venv: ## Create a virtual environment using uv
	$(PACKAGE_MANAGER) venv .venv
	$(PACKAGE_MANAGER) sync  


# --- Environment and Dependency Management (UV Optimized) ---
install: ## Install main dependencies using uv
	$(PACKAGE_MANAGER) pip install -r $(REQUIREMENTS)


# --- Development and Running ---
serve: ## Run the FastAPI application in development mode with auto-reload
	python main.py

# --- Testing and Quality Checks ---

# NOTE: Since the development dependencies (pytest, flake8, etc.) are installed
# into the environment, we can simply call them directly or use 'python -m' if needed.
test: ## Run tests using pytest
	pytest

lint: ## Run code style and quality checks (e.g., flake8, mypy)
	flake8 . 
	mypy .  --ignore-missing-imports

format: ## Format code using black and import sorting using isort
	black . 
	isort . 


# --- Cleanup ---

clean: ## Remove temporary and generated files
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf .pytest_cache .coverage .mypy_cache dist build

celery:
	celery -A src.core.celery_app worker --loglevel=info