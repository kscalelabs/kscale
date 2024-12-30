# Makefile

# ------------------------ #
#	   Static Checks	  #
# ------------------------ #

py-files := $(shell find . -type f -name '*.py' ! -path "./.venv/*")

format:
	@black $(py-files)
	@ruff format $(py-files)
	@isort $(py-files)
.PHONY: format

static-checks:
	@black --diff --check $(py-files)
	@ruff check $(py-files)
	@mypy --install-types --non-interactive $(py-files)
.PHONY: lint

# ------------------------ #
#		Unit tests		#
# ------------------------ #

test:
	python -m pytest
.PHONY: test
