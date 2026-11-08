# Учёт успеваемости студентов — вариант 8

Flask + PostgreSQL 16, веб-интерфейс и HTTP API. Версия разработки ЛР3 —
`0.3.0-dev`. Две Ubuntu Server без GUI, приложение через systemd от
`devopsapp`. Windows — SSH-клиент и браузер.

ЛР1 и ЛР2 сохранены в тегах `v0.1.0` и `v0.2.0`.
Новая функция ЛР3: комментарий к оценке до 500 символов и время новых записей.
Старые оценки сохраняются; неизвестные даты остаются NULL.

## Инструкции

- [Подготовка и обновление ВМ](docs/LR3.md).
- [Матрица функциональных требований и тестов](docs/LR3_TEST_MATRIX.md).
- [Результаты проверки и статус приёмки](docs/LR3_VALIDATION.md).
- [Сценарий защиты](docs/LR3_DEFENSE.md).
- [Правила изменения проекта](docs/RULES.md).
- [HTTP API](docs/API.md).
- [Историческая ЛР2](docs/LR2.md): для точного воспроизведения используйте v0.2.0.

## Запуск проверок

Python 3.12, PostgreSQL server/client 16. Зависимости закреплены в
requirements.txt и requirements-dev.txt.

```bash
make setup
```

Задайте DB_HOST, DB_PORT, DB_NAME=devops_test, DB_USER=devops_test
и интерактивно введите DB_PASSWORD по инструкции docs/LR3.md.
Копирование .env.test.example само по себе не загружает переменные.

```bash
make verify
```

Команда последовательно запускает Ruff formatter/linter, Bandit, unit/API/web-тесты,
покрытие, миграции чистой и заполненной БД, backup/damage/restore и два мутанта.
Любой провал завершает команду ошибкой. Отчёты — в reports/, вне Git.
Порог покрытия Python-кода — 70%; доля функций ТЗ оценивается отдельно по матрице.

Четыре выделенные тестовые БД: devops_test, devops_lr3_clean,
devops_lr3_upgrade, devops_lr3_restore. Их владелец — devops_test.
Проверки очищают эти базы. До очистки проверяются конфигурация и фактические
database/current_user/session_user.

## Команды

| Команда | Назначение |
|---|---|
| make setup | Venv, закреплённые зависимости, pip check |
| make run | Flask dev-server на 127.0.0.1:5001 с выбранной конфигурацией |
| make quality | Ruff format --check, Ruff check, Bandit |
| make test | Pytest, JUnit и XML/HTML/терминальный отчёт покрытия |
| make migrate | Выбранная БД → head через Alembic |
| make baseline | Проверка схемы ЛР2 и отметка 001_lr2 |
| make migration-check | Чистая и заполненная схемы, baseline, сохранение данных, downgrade/upgrade |
| make backup FILE=... | Custom-архив 0600; существующий файл не перезаписывается |
| make restore FILE=... CONFIRM_RESTORE=... | Явно подтверждённая целевая БД |
| make backup-check | Повреждение и восстановление данных, проверка identity |
| make mutation | Два контролируемых мутанта во временных копиях |
| make verify | Весь обязательный набор |

## Установка

Исходная миграция заморожена: 001_lr2 → 002_grade_comment →
003_comment_limit → 004_grade_created_at. Изменение schema.sql
не изменяет уже опубликованные миграции.

Основную devops обслуживает локальный postgres на db-server:
PRODUCTION=1 и Unix-сокет, DDL от devops_owner.
devops_app сохраняет минимальные SELECT/INSERT без CREATE.
Скрипт deploy/install-lr3-tools.sh устанавливает инструменты администратора
отдельно от runtime.

Приложение устанавливается deploy/install-app.sh.
Внешняя конфигурация — /etc/devops/app.env, root:root 600:
DB_HOST, APP_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT,
APP_VERSION, SECRET_KEY, ADMIN_PASSWORD.
Начальный admin создаётся идемпотентно без сброса пароля.

Адреса 192.0.2.x в публичной документации — примеры.
Секреты, ключи, дампы, venv и локальные отчёты в Git не включаются.
