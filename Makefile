.PHONY: default tests

export PYTHONPATH = $(realpath ./)
export ULEDGER3_SCRIPTS = $(realpath ./uledger3-scripts)

default: tests

tests:
	@python -m unittest discover --verbose
