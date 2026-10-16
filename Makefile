PYTHON ?= python

.PHONY: setup run test verify

setup:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) app.py

test:
	$(PYTHON) check.py

verify: test
	$(PYTHON) -c "import ast; from pathlib import Path; [ast.parse(Path(p).read_text(encoding='utf-8')) for p in ('app.py', 'check.py')]; print('syntax OK')"
