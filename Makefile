VIRTUALENV = virtualenv --python=python3
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python3
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -du)

.IGNORE: clean distclean maintainer-clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  install                     install dependencies and prepare environment"
	@echo "  build-requirements          install all requirements and freeze them in requirements.txt"
	@echo "  serve                       start the kinto server on default port"
	@echo "  flake8                      run the flake8 linter"
	@echo "  clean                       remove *.pyc files and __pycache__ directory"
	@echo "  distclean                   remove *.egg-info files and *.egg, build and dist directories"
	@echo "  maintainer-clean            remove the .tox and the .venv directories"
	@echo "Check the Makefile to know exactly what each target is doing."

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

build-requirements:
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue ".[monitoring,postgresql]"
	$(TEMPDIR)/bin/pip freeze | grep -v -- '-e' > requirements.txt

NAME := pollbot
SOURCE := $(shell git config remote.origin.url | sed -e 's|git@|https://|g' | sed -e 's|github.com:|github.com/|g')
VERSION := $(shell git describe --always --tag)
COMMIT := $(shell git log --pretty=format:'%H' -n 1)
version-file:
	echo '{"name":"$(NAME)","version":"$(VERSION)","source":"$(SOURCE)","commit":"$(COMMIT)"}' > version.json

serve: install version-file
	$(VENV)/bin/pollbot

flake8: install-dev
	$(VENV)/bin/flake8 kinto tests

clean:
	find . -name '__pycache__' -type d | xargs rm -fr

distclean: clean
	rm -fr *.egg *.egg-info/ dist/ build/

maintainer-clean: distclean
	rm -fr .venv/ .tox/
