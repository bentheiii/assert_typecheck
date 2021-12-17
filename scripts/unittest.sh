#!/bin/sh
# run the unittests with branch coverage
poetry run python -m pytest --cov-branch --cov=./assert_typecheck --cov-report=xml --cov-report=term-missing tests/
