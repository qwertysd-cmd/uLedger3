.PHONY: default unittests integrationtests

export PYTHONPATH = $(realpath ./)
export ULEDGER3_SCRIPTS = $(realpath ./uledger3-scripts)

default: unittests integrationtests

unittests:
	@echo ""
	@echo "Running unit tests."
	@echo ""
	@python -m unittest discover --verbose

integrationtests:
	@echo ""
	@echo "Running integration tests."
	@echo ""
	@find tests -type f -name run.sh | while read -r script; do \
	echo "Running $$script..."; \
	time bash "$$script" || { echo "Error: $$script failed"; exit 1; }; \
	done
