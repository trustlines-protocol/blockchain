VIRTUAL_ENV ?= venv

lint: install-requirements
	$(VIRTUAL_ENV)/bin/flake8 bridge_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/black --check bridge_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/mypy bridge_deploy tests setup.py --ignore-missing-imports

format:
	$(VIRTUAL_ENV)/bin/black bridge_deploy tests setup.py

test: install-requirements compile
	$(VIRTUAL_ENV)/bin/pytest tests

compile: .installed .compiled

POA_SOL_FILES=$(shell find ../submodules/poa-bridge-contracts/contracts -type f -iname '*.sol')
REWARD_SOL_FILES=$(shell find ../bridge/reward-contract/contracts -type f -iname '*.sol')
CONTRACT_SOL_FILES=$(shell find ../contracts/contracts -type f -iname '*.sol')
.compiled: ../submodules/poa-bridge-contracts/package.json $(POA_SOL_FILES) $(REWARD_SOL_FILES) $(CONTRACT_SOL_FILES) $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/deploy-tools compile --evm-version petersburg -d ../bridge/reward-contract/contracts -o build/reward.json
	$(VIRTUAL_ENV)/bin/deploy-tools compile --evm-version petersburg -d ../contracts/contracts -o build/contracts.json
	$(VIRTUAL_ENV)/bin/npm --prefix ../submodules/poa-bridge-contracts install && \
	cd ../submodules/poa-bridge-contracts && \
	./node_modules/.bin/truffle compile --all
	@echo "This file controls for make if the contracts are up to date" > $@

build: compile
	$(VIRTUAL_ENV)/bin/python setup.py sdist

install-requirements: .installed

install: install-requirements compile
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -e .

.installed: constraints.txt requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -r requirements.txt
	$(VIRTUAL_ENV)/bin/nodeenv --node=8.16.0 --prebuilt -p
	git submodule init
	git submodule update
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

.PHONY: install install-requirements test lint compile build format
