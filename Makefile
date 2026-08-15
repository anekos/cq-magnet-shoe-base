.PHONY: watch
watch:
	axe src/**/*.py -- uv run magnet-shoe-base -- build --show

.PHONY: build
build:
	axe src/**/*.py -- uv run magnet-shoe-base -- build
