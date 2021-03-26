# project settings
PROJECT_NAME  := $(shell grep -m1 'APPNAME' */settings.py | cut -f2 -d'"')
PROJECT_PATH  := $(shell ls */settings.py | xargs dirname | head -n 1)

export PYTHONPATH := $(PROJECT_PATH)

clean:
	rm -rf dependencies .pytest_cache .coverage packaged.yaml
	find $(PROJECT_PATH) -name __pycache__ | xargs rm -rf
	find tests -name __pycache__ | xargs rm -rf

install-hook:
	@echo "make lint" > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit

install-dev: install install-hook
	if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

install:
	if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

lint:
	black --line-length=90 --target-version=py38 --check .
	flake8 --max-line-length=90 --ignore=E402 --exclude .venv,dependencies

format:
	black --line-length=90 --target-version=py38 .

test:
	coverage run --source=$(PROJECT_PATH) --omit=dependencies -m unittest

coverage: test .coverage
	coverage report --fail-under=80
