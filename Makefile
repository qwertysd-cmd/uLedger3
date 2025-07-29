.PHONY: default tests

default: tests

tests:
	@python -m unittest discover --verbose
