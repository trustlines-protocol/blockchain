TOP_LEVEL=$(shell cd ../..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv
CONTRACTS_DIRECTORY=$(TOP_LEVEL)/contracts/contracts

lint: install
	$(VIRTUAL_ENV)/bin/flake8 --config $(TOP_LEVEL)/.flake8 src tests setup.py
	$(VIRTUAL_ENV)/bin/black --check src tests setup.py
	$(VIRTUAL_ENV)/bin/mypy src tests setup.py --ignore-missing-imports

test: install
	$(VIRTUAL_ENV)/bin/pytest tests

compile: install-requirements
	$(VIRTUAL_ENV)/bin/deploy-tools compile --evm-version petersburg --optimize --optimize-runs 100 -d $(CONTRACTS_DIRECTORY)
	$(VIRTUAL_ENV)/bin/python scripts/pack_contracts.py build/contracts.json src/auction_deploy/contracts.json

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
	rm -f .installed src/auction_deploy/contracts.json

.PHONY: install install-requirements test lint compile build clean
