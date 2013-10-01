.PHONY: pep8
pep8:
	find . -name \*.py | xargs pep8 --ignore=E501
	pep8 --ignore=E501 scripts/flightrecorder

.PHONY: deb
deb:
	debuild --no-tgz-check -uc -us

.PHONY: pypi-upload
pypi-upload:
	python setup.py sdist upload
