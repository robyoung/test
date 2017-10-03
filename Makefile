
.PHONY: test
test: requirements
	python test.py

.PHONY: requirements
requirements:
	pip install -r requirements.txt
