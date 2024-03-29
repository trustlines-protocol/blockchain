TOP_LEVEL=$(shell cd ..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv
CONTRACTS_DIRECTORY=$(TOP_LEVEL)/contracts/contracts

lint: install-requirements
	$(VIRTUAL_ENV)/bin/flake8 tests
	$(VIRTUAL_ENV)/bin/black --check tests

test: install
	$(VIRTUAL_ENV)/bin/pytest tests

compile: install-requirements
	$(VIRTUAL_ENV)/bin/deploy-tools compile -d $(CONTRACTS_DIRECTORY)

build: compile

install-requirements: .installed

install: install-requirements compile

.installed: requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -r requirements.txt pip wheel setuptools
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

clean:
	rm -rf build .tox .mypy_cache .pytest_cache */__pycache__ tests/*/__pycache__ *.egg-info
	rm -f .installed

.PHONY: install install-requirements test lint compile build clean
