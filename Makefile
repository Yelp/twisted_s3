.PHONY: docs test clean

test:
	tox

docs:
	tox -e docs

clean:
	find . -name '*.pyc' -delete
	rm -rf twisted_s3.egg-info
	rm -rf docs/build
	rm -f MANIFEST
