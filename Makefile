# project settings
PROJECT_PATH := serpens

# venv settings
export PYTHONPATH := $(PROJECT_PATH):tests/fixtures
export VIRTUALENV := $(PWD)/.venv
export PATH       := $(VIRTUALENV)/bin:$(PATH)

# unittest logging level
test: export LOG_LEVEL=CRITICAL

# fix make < 3.81 (macOS and old Linux distros)
ifeq ($(filter undefine,$(value .FEATURES)),)
SHELL = env PATH="$(PATH)" /bin/bash
endif

.PHONY: .env .venv

build:
	python3.8 -m build

.env:
	echo 'PYTHONPATH="$(PYTHONPATH)"' > .env

.venv:
	python3.8 -m venv $(VIRTUALENV)
	$(VIRTUALENV)/bin/pip install --upgrade pip

clean:
	rm -rf dependencies .pytest_cache .coverage .aws-sam build dist .mypy_cache *.egg-info
	find $(PROJECT_PATH) -name __pycache__ | xargs rm -rf
	find tests -name __pycache__ | xargs rm -rf

install-hook:
	@echo "make lint" > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit

install-dev: .venv .env install install-hook
	if [ -f requirements-dev.txt ]; then $(VIRTUALENV)/bin/pip install -r requirements-dev.txt; fi

install:
	if [ -f requirements.txt ]; then $(VIRTUALENV)/bin/pip install -r requirements.txt; fi

lint:
	black --line-length=100 --target-version=py38 --check .
	flake8 --max-line-length=100 --ignore=E402,W503,E712 --exclude .venv,dependencies

format:
	black --line-length=100 --target-version=py38 .

test:
	coverage run --source=$(PROJECT_PATH) --omit=dependencies -m unittest

coverage: test .coverage
	coverage report -m --fail-under=90

check:
	twine check dist/*
