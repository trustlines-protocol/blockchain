TOP_LEVEL=$(shell cd ../..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv
CONTRACTS_DIRECTORY=$(TOP_LEVEL)/contracts/contracts

lint: install-requirements
	$(VIRTUAL_ENV)/bin/flake8 bridge_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/black --check bridge_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/mypy bridge_deploy tests setup.py --ignore-missing-imports

format:
	$(VIRTUAL_ENV)/bin/black bridge_deploy tests setup.py

test: install-requirements compile
	$(VIRTUAL_ENV)/bin/pytest tests

compile: .installed .compiled

POA_SOL_FILES=$(shell find $(TOP_LEVEL)/submodules/poa-bridge-contracts/contracts -type f -iname '*.sol')
CONTRACT_SOL_FILES=$(shell find $(CONTRACTS_DIRECTORY) -type f -iname '*.sol')
.compiled: $(TOP_LEVEL)/submodules/poa-bridge-contracts/package.json $(POA_SOL_FILES) $(CONTRACT_SOL_FILES) $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/deploy-tools compile --evm-version petersburg -d $(CONTRACTS_DIRECTORY) -o build/contracts.json
	$(VIRTUAL_ENV)/bin/npm --prefix $(TOP_LEVEL)/submodules/poa-bridge-contracts install && \
	cd $(TOP_LEVEL)/submodules/poa-bridge-contracts && \
	./node_modules/.bin/truffle compile --all
	@echo "This file controls for make if the contracts are up to date" > $@

build: compile
	$(VIRTUAL_ENV)/bin/python setup.py sdist

install-requirements: .installed

install: install-requirements compile
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -e .

.installed: constraints.txt requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt pip wheel setuptools
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -r requirements.txt
	$(VIRTUAL_ENV)/bin/nodeenv --node=8.16.0 --prebuilt -p
	git submodule init
	git submodule update
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

clean:
	rm -rf build .tox .mypy_cache .pytest_cache */__pycache__ *.egg-info
	rm -f .installed .compiled
	git submodule deinit --all -f

.PHONY: install install-requirements test lint compile build format clean
