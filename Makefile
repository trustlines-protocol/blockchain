VIRTUAL_ENV ?= $(shell pwd)/venv

SUBDIRS = tools/auction-deploy tools/bridge-deploy tools/validator-set-deploy contracts

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
