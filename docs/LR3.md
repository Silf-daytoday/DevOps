# ЛР3. Автоматические проверки, миграции и резервное копирование

Стек: Ubuntu Server 24.04 без GUI, Python 3.12, PostgreSQL 16.
Выполняется на существующих APP/DB ЛР2. Контейнеры и CI в эту работу не добавлены.
Адреса 192.0.2.1/.10/.20 и имя devopsadmin — публичные примеры.
Подставьте реальные адреса и SSH-пользователя своего стенда.
Не переносите примеры адресов в уже работающий Netplan.

## 1. Получить исходники на ВМ

Исходный архив — devops-lr3-source.tar.gz. Git-история поставляется отдельно
в devops-lr3.bundle; публиковать ветку следует после проверок на целевом стенде.

PowerShell Windows, отдельное локальное окно:

```powershell
scp -i "$env:USERPROFILE\.ssh\devops_lr2" "$env:USERPROFILE\Downloads\devops-lr3-source.tar.gz" devopsadmin@192.0.2.10:~/
scp -i "$env:USERPROFILE\.ssh\devops_lr2" "$env:USERPROFILE\Downloads\devops-lr3-source.tar.gz" devopsadmin@192.0.2.20:~/
```

Подключитесь к APP и DB в двух отдельных окнах. На каждой ВМ:

```bash
mkdir -p ~/devops-lr3
tar -xzf ~/devops-lr3-source.tar.gz -C ~/devops-lr3
cd ~/devops-lr3
```

На APP:

```bash
sudo apt update
sudo apt install -y python3-venv make postgresql-client-16
```

На DB для административных Python-инструментов:

```bash
sudo apt update
sudo apt install -y python3-venv make
```

## 2. Тестовые БД — SSH DB

Выполните SQL через stdin: файл читает административная оболочка,
postgres не требуется доступ в домашний каталог SSH-пользователя.

```bash
cd ~/devops-lr3
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 < deploy/03-lr3-test-databases.sql
```

Будут подготовлены devops_test/devops_lr3_clean/devops_lr3_upgrade/
devops_lr3_restore. Все принадлежат devops_test, без SUPERUSER/CREATEDB/CREATEROLE.
Основная devops не изменяется. Существующий пароль не сбрасывается.
Если роль создаётся впервые, задайте пароль интерактивно в psql через
`\password devops_test`.

Откройте:

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Добавьте перед общими запрещающими правилами (если они есть):

```text
host devops_lr3_clean,devops_lr3_upgrade,devops_lr3_restore devops_test 192.0.2.10/32 scram-sha-256
```

Существующее правило devops_test сохраните.
Проверьте и перечитайте конфигурацию:

```bash
sudo -u postgres psql -c "SELECT line_number,error FROM pg_hba_file_rules WHERE error IS NOT NULL;"
sudo systemctl reload postgresql@16-main
pg_lsclusters
```

При ошибках конфигурации сначала исправьте их.
UFW уже допускает PostgreSQL с APP; разрешение для Windows на 5432 не добавляется.

## 3. Полная проверка — SSH APP

```bash
cd ~/devops-lr3
make setup
. .venv/bin/activate
export DB_HOST=192.0.2.20
export DB_PORT=5432
export DB_NAME=devops_test
export DB_USER=devops_test
export APP_VERSION=0.3.0-dev
read -rsp 'Пароль devops_test: ' DB_PASSWORD
printf '\n'
export DB_PASSWORD
make verify
```

При успехе: 137 passed, порог 70% пройден, MIGRATION CLEAN/POPULATED OK,
BACKUP + DAMAGE + RESTORE ... OK, два MUTATION KILLED, финальное VERIFY OK.
При новых изменениях число тестов может вырасти; ориентируйтесь на отсутствие
провалов и успешное завершение всех стадий.
Отдельная сохранённая регрессия ЛР2:

```bash
python check.py
```

Отчёты: reports/junit.xml, reports/coverage.xml, reports/htmlcov/index.html,
reports/bandit.json. Они не включаются в Git.
Переменные этой SSH-сессии не меняют EnvironmentFile установленного сервиса.
Если проверка не прошла, основную БД и установленное приложение не обновляйте.

## 4. Миграции

001_lr2 — замороженная исходная схема шести таблиц.
002 — nullable comment.
003 — CHECK длины comment <= 500.
004 — nullable created_at и CURRENT_TIMESTAMP для новых строк;
существующие неизвестные даты сохраняются как NULL.

make migration-check работает только с выделенными clean/upgrade БД.
Он проверяет создание с нуля, baseline заполненной ЛР2, точное сохранение
исходных оценок и downgrade/upgrade тестовой схемы.

Baseline сравнивает имена/типы/NOT NULL/identity/default столбцов и определения
PK/FK/UNIQUE/CHECK с сохранённой сигнатурой PostgreSQL 16.
При дополнительном столбце, изменённом ограничении или другом владельце
основных таблиц выполнение прекращается до stamp.
Сам baseline только создаёт запись 001_lr2 в alembic_version.
Использовать stamp head вместо проверки исходного состояния нельзя.

## 5. Основная БД: инструменты и резервная копия — SSH DB

После успешного verify установите отдельные инструменты администратора:

```bash
cd ~/devops-lr3
sudo bash deploy/install-lr3-tools.sh
cd /opt/devops/lr3-tools
lr3_backup="/var/backups/devops/devops-before-lr3-$(date +%Y%m%d-%H%M%S).dump"
sudo -u postgres env DB_HOST=/var/run/postgresql DB_PORT=5432 DB_NAME=devops DB_USER=postgres make backup PRODUCTION=1 FILE="$lr3_backup"
printf '%s\n' "$lr3_backup"
sudo -u postgres pg_restore --list "$lr3_backup"
```

Сохраните путь. Файл создаётся эксклюзивно с 0600; существующая копия
не перезаписывается. Не помещайте дамп в Git.
Сохраните контрольное состояние:

```bash
sudo -u postgres psql -d devops -c "SELECT 'groups' AS entity, COUNT(*) FROM groups UNION ALL SELECT 'students',COUNT(*) FROM students UNION ALL SELECT 'grades',COUNT(*) FROM grades;"
```

## 6. Обновить основную схему

На APP остановите сервис:

```bash
sudo systemctl stop devops-app
```

На DB из /opt/devops/lr3-tools:

```bash
sudo -u postgres env DB_HOST=/var/run/postgresql DB_PORT=5432 DB_NAME=devops DB_USER=postgres make baseline PRODUCTION=1
sudo -u postgres env DB_HOST=/var/run/postgresql DB_PORT=5432 DB_NAME=devops DB_USER=postgres make migrate PRODUCTION=1
sudo -u postgres psql -d devops -c "TABLE alembic_version;"
sudo -u postgres psql -d devops -c "SELECT 'groups' AS entity, COUNT(*) FROM groups UNION ALL SELECT 'students',COUNT(*) FROM students UNION ALL SELECT 'grades',COUNT(*) FROM grades;"
```

Ожидаемая ревизия — 004_grade_created_at; количество исходных записей сохраняется.
Baseline нужен один раз для ещё не версионированной ЛР2.
Если схема уже имеет alembic_version, повторный baseline откажет:
проверьте фактическую ревизию, а не удаляйте таблицу версий.

Миграции выполняются в транзакции от devops_owner через локального postgres.
Runtime devops_app получает SELECT/INSERT шести предметных таблиц и USAGE
последовательностей. alembic_version не выдаётся приложению как рабочая таблица.
Права CREATE для runtime не добавляются.

## 7. Установить приложение — SSH APP

```bash
cd ~/devops-lr3
sudo bash deploy/install-app.sh
sudo nano /etc/devops/app.env
```

Измените APP_VERSION на 0.3.0-dev. Остальные рабочие значения сохраните.
Установщик копирует app.py и domain.py, использует закреплённые runtime-зависимости,
сохраняет существующий app.env. Служба и владелец devopsapp остаются теми же.

```bash
sudo systemctl enable --now devops-app
sudo systemctl status devops-app --no-pager
curl -i http://192.0.2.10:5000/health
curl http://192.0.2.10:5000/version
```

Покажите в браузере Windows старые данные и вход.
Создайте новую оценку для подходящей связки студент/дисциплина/семестр
с учебным планом и комментарием. Проверьте отображение комментария/времени.
Для старых оценок неизвестная дата отображается тире.
После restart данные сохраняются.

## 8. Демонстрация восстановления — SSH APP

Используйте тестовую конфигурацию из раздела 3, пароль devops_test.
Подготовьте контрольные данные и выберите только restore-БД:

```bash
cd ~/devops-lr3
make backup-check
export DB_NAME=devops_lr3_restore
lr3_demo_file="$PWD/backups/defense-$(date +%Y%m%d-%H%M%S).dump"
make backup FILE="$lr3_demo_file"
psql -h "$DB_HOST" -p "$DB_PORT" -U devops_test -d devops_lr3_restore -W -c "SELECT id,name FROM groups ORDER BY id;"
psql -h "$DB_HOST" -p "$DB_PORT" -U devops_test -d devops_lr3_restore -W -c "UPDATE groups SET name='LR3-DAMAGED' WHERE name='LR3-CONTROL' RETURNING id,name;"
make restore FILE="$lr3_demo_file" CONFIRM_RESTORE=devops_lr3_restore
psql -h "$DB_HOST" -p "$DB_PORT" -U devops_test -d devops_lr3_restore -W -c "SELECT id,name FROM groups ORDER BY id;"
export DB_NAME=devops_test
```

Контрольное имя восстановится. Автоматический backup-check дополнительно
сравнивает все шесть таблиц, комментарий и работу identity после восстановления.

Аварийное восстановление ОСНОВНОЙ devops — отдельная административная операция
на DB при остановленном приложении. Требуются локальный postgres,
PRODUCTION=1, FILE=путь и CONFIRM_RESTORE=devops:
`make restore PRODUCTION=1 FILE=... CONFIRM_RESTORE=devops`.
Скрипт возвращает runtime-права после восстановления.
Если восстановлена копия схемы ЛР2, для запуска нужен соответствующий код v0.2.0.
Для обычной демонстрации используйте выделенную restore-БД выше.

## 9. Git и выпуск

Импорт bundle выполняется в чистую рабочую копию Windows. Сначала переключитесь
на develop, чтобы импортируемая feature-ветка не была открыта:

```powershell
Set-Location "$env:USERPROFILE\DevOps-LR2-Git"
git status --short
git fetch origin --tags
git switch develop
git pull --ff-only origin develop
git fetch "$env:USERPROFILE\Downloads\devops-lr3.bundle" "refs/heads/feature/lr3-verification-migrations-backup:refs/heads/feature/lr3-verification-migrations-backup"
git switch feature/lr3-verification-migrations-backup
git config user.name "Silf-daytoday"
git config user.email "shcheblykin06@bk.ru"
git log -5 --format="%h | %an <%ae> | %cn <%ce> | %s"
```

Если status непустой или импорт не fast-forward, остановитесь и сохраните
имеющиеся изменения; force/reset не требуются.
После реального успешного verify и проверки установленного приложения:

```powershell
git push -u origin feature/lr3-verification-migrations-backup
```

PR: feature → develop. В описание добавьте номер Issue и фактические результаты
ВМ. Следом release/0.3.0 от обновлённого develop, APP_VERSION 0.3.0
в коде/шаблоне/документации и установленном env, повторный verify,
PR release → main и release → develop. Create a merge commit сохраняет историю.
Тег v0.3.0 ставится на принятый main; старые теги сохраняются.
Release-ветка и финальный тег заранее не созданы.

## 10. Анализаторы и проверочные ограничения

Ruff check проверяет E4/E7/E9/F/I; форматтер запускается отдельно в --check.
Bandit сканирует production-код app.py/domain.py, lr3_tools и миграции.
Фикстуры с учебными данными не являются production-кодом.
Исключения: import subprocess (B404) и два вызова subprocess.run (B603)
в backup.py/mutation.py. Это необходимые ложные срабатывания:
абсолютные исполняемые пути, закрытый список pg_dump/pg_restore либо текущий Python,
список argv, shell=False, имена БД проверены, пароль только в окружении.
Причины указаны у соответствующих строк. Глобального отключения правил нет.

Из отчёта покрытия исключён только блок ручного запуска Flask dev-server
под if __name__ == "__main__": служба Gunicorn импортирует приложение,
а рабочие маршруты и бизнес-логика полностью учитываются. Mako-шаблон
исключён из Ruff как шаблон, который ещё не является готовым Python.

Порог покрытия кода 70% зафиксирован в pyproject.toml, skip/xfail не используются.
Функциональное покрытие — отдельная матрица docs/LR3_TEST_MATRIX.md.
Безусловная очистка схемы допускается только после проверки четырёх тестовых
имён и реальной роли devops_test. Основную БД make verify не обслуживает.

Официальные справки:
- https://alembic.sqlalchemy.org/en/latest/tutorial.html
- https://alembic.sqlalchemy.org/en/latest/api/commands.html
- https://docs.pytest.org/en/stable/
- https://docs.astral.sh/ruff/
- https://bandit.readthedocs.io/
- https://www.postgresql.org/docs/16/app-pgdump.html
- https://www.postgresql.org/docs/16/app-pgrestore.html
