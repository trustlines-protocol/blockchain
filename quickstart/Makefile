TOP_LEVEL=$(shell cd ..; pwd)
VIRTUAL_ENV ?= $(TOP_LEVEL)/venv

lint: install
	$(VIRTUAL_ENV)/bin/flake8 quickstart setup.py
	$(VIRTUAL_ENV)/bin/black --check quickstart setup.py

test: install
	$(VIRTUAL_ENV)/bin/pytest tests

install-requirements: .installed

install: install-requirements
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -e .

.installed: constraints.txt requirements.txt $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt pip wheel setuptools
	$(VIRTUAL_ENV)/bin/pip install -c constraints.txt -r requirements.txt
	@echo "This file controls for make if the requirements in your virtual env are up to date" > $@

$(VIRTUAL_ENV):
	python3 -m venv $@

clean:
	rm -rf build .tox .mypy_cache .pytest_cache */__pycache__ */*/__pycache__ *.egg-info */*.egg-info
	rm -f .installed

build-docker-image::
	docker build -t quickstart ../. -f Dockerfile

.PHONY: install install-requirements test lint compile build clean build-docker-image
