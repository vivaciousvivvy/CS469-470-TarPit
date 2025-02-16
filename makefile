format:
	isort .
	black .

lint:
	flake8 .
	pylint *.py

check: format lint

run:
	python main.py