all:

test:
	coverage run --source=serpens -m pytest

coverage: .coverage
	coverage report --fail-under=90
