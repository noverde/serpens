all:

test:
	coverage run --source=serpens -m pytest
	@rm -f ./serpens/test.db

coverage: .coverage
	coverage report --fail-under=90
