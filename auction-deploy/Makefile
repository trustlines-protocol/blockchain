VIRTUAL_ENV ?= venv

lint: install
	$(VIRTUAL_ENV)/bin/flake8 auction_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/black --check auction_deploy tests setup.py
	$(VIRTUAL_ENV)/bin/mypy auction_deploy tests setup.py --ignore-missing-imports

test: install
	$(VIRTUAL_ENV)/bin/pytest tests

compile: install-requirements
	$(VIRTUAL_ENV)/bin/deploy-tools compile -d ../contracts/contracts
	$(VIRTUAL_ENV)/bin/python scripts/pack_contracts.py build/contracts.json auction_deploy/contracts.json

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
