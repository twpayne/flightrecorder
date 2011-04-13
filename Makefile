.PHONY: deb
deb:
	debuild --no-tgz-check -uc -us
