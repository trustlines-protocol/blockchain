TOP_LEVEL=$(shell cd ../..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv
CONTRACTS_DIRECTORY=$(TOP_LEVEL)/contracts/contracts

lint: install-requirements
	$(VIRTUAL_ENV)/bin/flake8 src tests setup.py
	$(VIRTUAL_ENV)/bin/black --check src tests setup.py
	$(VIRTUAL_ENV)/bin/mypy src tests setup.py --ignore-missing-imports

format:
	$(VIRTUAL_ENV)/bin/black src tests setup.py

test: install compile
	$(VIRTUAL_ENV)/bin/pytest tests

compile: .installed .compiled

CONTRACT_SOL_FILES=$(shell find $(CONTRACTS_DIRECTORY) -type f -iname '*.sol')
.compiled: $(CONTRACT_SOL_FILES) $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/deploy-tools compile --evm-version petersburg --optimize-runs 5000 -d $(CONTRACTS_DIRECTORY) -o src/bridge_deploy/contracts.json
	@echo "This file controls for make if the contracts are up to date" > $@

build: compile
	$(VIRTUAL_ENV)/bin/python setup.py sdist

install-requirements: .installed

install: install-requirements compile
	$(VIRTUAL_ENV)/bin/pip install -r requirements.txt -e .

.installed: requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -r requirements.txt pip wheel setuptools
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

clean:
	rm -rf build .tox .mypy_cache .pytest_cache */__pycache__ */*/__pycache__ *.egg-info */*.egg-info
	rm -f .installed .compiled src/bridge_deploy/contracts.json

.PHONY: install install-requirements test lint compile build format clean
