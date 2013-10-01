SRC = $(shell find flightrecorder tests -name \*.py) scripts/flightrecorder

.PHONY: all
all: pep8 pyflakes

.PHONY: pep8
pep8:
	pep8 --ignore=E501 $(SRC)

.PHONY: pyflakes
pyflakes:
	pyflakes $(SRC)

.PHONY: deb
deb:
	debuild --no-tgz-check -uc -us

.PHONY: pypi-upload
pypi-upload:
	python setup.py sdist upload
