TOP_LEVEL=$(shell cd ../..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv
CONTRACTS_DIRECTORY=$(TOP_LEVEL)/contracts/contracts

lint: install
	$(VIRTUAL_ENV)/bin/flake8 validator_set_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/black --check validator_set_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/mypy validator_set_deploy tests setup.py --ignore-missing-imports

test: install
	$(VIRTUAL_ENV)/bin/pytest tests

compile: install-requirements
	$(VIRTUAL_ENV)/bin/deploy-tools compile --evm-version petersburg -d $(CONTRACTS_DIRECTORY)
	$(VIRTUAL_ENV)/bin/python scripts/pack_contracts.py build/contracts.json validator_set_deploy/contracts.json

build: compile
	$(VIRTUAL_ENV)/bin/python setup.py sdist

install-requirements: .installed

install: install-requirements compile
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -e .

.installed: constraints.txt requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -r requirements.txt
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

.PHONY: install install-requirements test lint compile build
