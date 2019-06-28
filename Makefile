DC := $(shell which docker-compose)

.PHONY: help
help: default

.PHONY: default
default:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo ""
	@echo "  build       - build local dev environment"
	@echo "  run         - start the kinto server on default port"
	@echo "  lint        - run the linter"
	@echo "  test        - run tests"
	@echo "  shell       - run a bash shell in the container"
	@echo "  clean       - remove build artifacts"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."

.docker-build:
	make build

.PHONY: build
build: .env
	${DC} build app
	touch .docker-build

.env:
	@if [ ! -f .env ]; \
	then \
	echo "Copying env-dist to .env..."; \
	cp env-dist .env; \
	fi

SOURCE := $(shell git config remote.origin.url | sed -e 's|git@|https://|g' | sed -e 's|github.com:|github.com/|g')
VERSION := $(shell git describe --always --tag)
COMMIT := $(shell git log --pretty=format:'%H' -n 1)

.PHONY: version-file
version-file:
	echo '{"build":"Manual build","version":"$(VERSION)","source":"$(SOURCE)","commit":"$(COMMIT)"}' > version.json

.PHONY: install-local
install-local:
# Need to do this to create the pollbot.egg-info in the repo directory.
# FIXME(willkg): This is gross, but "works".
	${DC} run --rm --user 0 app pip install -e /app

.PHONY: run
run: .docker-build .env version-file install-local
	${DC} run --rm app /usr/local/bin/pollbot

.PHONY: test
test: .docker-build .env install-local
	${DC} run --rm --no-deps app /bin/bash -c "/usr/local/bin/pytest tests -s"

.PHONY: lint
lint: .docker-build .env
	${DC} run --rm --no-deps app /bin/bash -c "/usr/local/bin/flake8 pollbot tests"

.PHONY: shell
shell: .docker-build .env
	${DC} run --rm --no-deps app /bin/bash

clean:
	rm .docker-build
