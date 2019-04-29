VIRTUAL_ENV ?= venv

lint: install
	$(VIRTUAL_ENV)/bin/flake8 tests
	$(VIRTUAL_ENV)/bin/black --check tests

test: install compile
	$(VIRTUAL_ENV)/bin/pytest tests

compile: install
	$(VIRTUAL_ENV)/bin/deploy-tools compile -d ../contracts/contracts
	$(VIRTUAL_ENV)/bin/python scripts/pack_contracts.py build/contracts.json auction_deploy/contracts.json

build: compile
	$(VIRTUAL_ENV)/bin/python setup.py sdist

install: .installed

.installed: constraints.txt requirements.txt venv
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -r requirements.txt
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

venv:
	python3 -m venv $@

.PHONY: install test lint compile build
