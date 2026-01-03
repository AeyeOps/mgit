.PHONY: help test lint format build build-install install clean version test-binary

# Default target - show help
help:
	@uv run python scripts/make.py

test:
	@uv run python scripts/make.py test $(ARGS)

lint:
	@uv run python scripts/make.py lint $(ARGS)

format:
	@uv run python scripts/make.py format $(ARGS)

build:
	@uv run python scripts/make.py build $(ARGS)

build-install:
	@uv run python scripts/make.py build --target linux --install

install: build-install

clean:
	@uv run python scripts/make.py clean

version:
	@uv run python scripts/make.py version $(ARGS)

test-binary:
	@uv run python scripts/make.py test-binary $(ARGS)
