all: test

test:
	pytest --cov=./ templates -vv

test-ui:
	pytest --cov=./ --cov-report=html templates
