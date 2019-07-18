VIRTUAL_ENV ?= $(shell pwd)/venv

SUBDIRS = tools/auction-deploy tools/bridge-deploy tools/validator-set-deploy tools/quickstart tools/bridge contracts

.PHONY: help
help:
	@echo "You can build any of the following targets. The clean, install, lint and test targets will run those targets for all subfolders.  The clean-*, install-*, lint-*, test-* targets will will run in the respective subfolder only:\n" |fold -s

	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

	@echo "\npython packages will be installed into the virtualenv in $(VIRTUAL_ENV)\n" |fold -s

SUB_INSTALL = $(addprefix install-,$(SUBDIRS))
install: setup-venv $(SUB_INSTALL)
$(SUB_INSTALL): install-%: setup-venv
	@echo "==> Installing $*"
	$(MAKE) -C $* install
.PHONY: install $(SUB_INSTALL)

SUB_CLEAN = $(addprefix clean-,$(SUBDIRS))
clean: $(SUB_CLEAN)
	rm -rf venv
$(SUB_CLEAN): clean-%:
	@echo "==> Cleaning $*"
	$(MAKE) -C $* clean
.PHONY: clean $(SUB_CLEAN)

SUB_LINT = $(addprefix lint-,$(SUBDIRS))
lint: setup-venv $(SUB_LINT)
$(SUB_LINT): lint-%: setup-venv
	@echo "==> Linting $*"
	$(MAKE) -C $* lint
.PHONY: lint $(SUB_LINT)

SUB_TEST = $(addprefix test-,$(SUBDIRS))
test: setup-venv $(SUB_TEST)
$(SUB_TEST): test-%: setup-venv
	@echo "==> Testing $*"
	$(MAKE) -C $* test
.PHONY: test $(SUB_TEST)


$(VIRTUAL_ENV):
	@echo "==> Creating virtualenv in $(VIRTUAL_ENV)"
	python3 -m venv $@

setup-venv: $(VIRTUAL_ENV)
	@echo "==> Using virtualenv in $(VIRTUAL_ENV)"

.PHONY: setup-venv
