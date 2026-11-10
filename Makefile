PYTHON ?= .venv/bin/python
PRODUCTION ?= 0
FILE ?=
CONFIRM_RESTORE ?=
ifeq ($(PRODUCTION),1)
PROD_FLAG = --production
endif

.PHONY: setup run test quality migrate baseline backup restore migration-check backup-check mutation container-check verify

setup:
	bash scripts/setup.sh

run:
	APP_HOST=127.0.0.1 PORT=5001 $(PYTHON) app.py

quality:
	mkdir -p reports
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m bandit -r app.py domain.py lr3_tools migrations -f json -o reports/bandit.json

migrate:
	$(PYTHON) -m lr3_tools migrate $(PROD_FLAG)

baseline:
	$(PYTHON) -m lr3_tools baseline $(PROD_FLAG)

test:
	mkdir -p reports
	$(PYTHON) -m pytest --cov=app --cov=domain --cov-report=term-missing --cov-report=xml:reports/coverage.xml --cov-report=html:reports/htmlcov --junitxml=reports/junit.xml

migration-check:
	$(PYTHON) -m lr3_tools migration-check

backup-check:
	$(PYTHON) -m lr3_tools backup-check

backup:
	$(PYTHON) -m lr3_tools backup $(PROD_FLAG) --file "$(FILE)"

restore:
	$(PYTHON) -m lr3_tools restore $(PROD_FLAG) --file "$(FILE)" --confirm "$(CONFIRM_RESTORE)"

mutation:
	$(PYTHON) -m lr3_tools.mutation

container-check:
	bash scripts/container-check.sh
# Последовательность явная: следующий этап не скрывает ошибку предыдущего.
# Все обращения к БД внутри verify используют только тестовую конфигурацию.
verify:
	$(MAKE) quality
	$(MAKE) test
	$(MAKE) migration-check
	$(MAKE) backup-check
	$(MAKE) mutation
	$(MAKE) container-check
	@echo "VERIFY OK: quality, tests, migrations, backup/restore, mutation, containers"
