.PHONY: test build build-install install

test:
	uv run pytest

build:
	uv run python scripts/make_build.py --target linux

build-install:
	uv run python scripts/make_build.py --target linux --install

install: build-install
