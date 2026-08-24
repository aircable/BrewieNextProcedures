.PHONY: validate test bundle clean

validate:
	python3 scripts/validate.py

test:
	python3 -m unittest discover -s tests -v

bundle: validate test
	python3 scripts/build_bundle.py

clean:
	rm -rf dist

