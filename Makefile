.PHONY: interactive
interactive:
	uv run magnet-shoe-base -- interactive

.PHONY: build
build:
	axe src/**/*.py -- uv run magnet-shoe-base -- build

.PHONY: watch
watch:
	axe src/**/*.py -- uv run magnet-shoe-base -- build --show

.PHONY: setup
setup:
	uv sync
	uv run pre-commit install
