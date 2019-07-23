TOP_LEVEL=$(shell cd ../..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv

lint: install-requirements
	$(VIRTUAL_ENV)/bin/flake8 bridge tests setup.py
	$(VIRTUAL_ENV)/bin/black --check bridge tests setup.py
	$(VIRTUAL_ENV)/bin/mypy bridge tests setup.py --ignore-missing-imports

format:
	$(VIRTUAL_ENV)/bin/black bridge tests setup.py

test: install-requirements install
	$(VIRTUAL_ENV)/bin/pytest tests

build: install
	$(VIRTUAL_ENV)/bin/python setup.py sdist

start: install
	$(VIRTUAL_ENV)/bin/tlbc-bridge

install-requirements: .installed

install: install-requirements compile
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -e .

.installed: constraints.txt requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt pip wheel setuptools
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -r requirements.txt
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

clean:
	rm -rf build .tox .mypy_cache .pytest_cache */__pycache__ *.egg-info
	rm -f .installed

.PHONY: install install-requirements test lint compile build format clean start
