.PHONY: deb
deb:
	debuild --no-tgz-check -uc -us

.PHONY: pypi-upload
pypi-upload:
	python setup.py sdist upload
