# ЛР1 — Учёт успеваемости студентов (Вариант 8)

Команда из 2 человек. Приложение: Flask + SQLite (реляционная БД), HTTP API + веб-интерфейс.

## Быстрый старт
1. Установить Python 3.10+.
2. `pip install -r requirements.txt`
3. Скопировать настройки: Windows — `copy .env.example .env`, Linux/Mac — `cp .env.example .env`
4. Запустить: `python app.py`
5. Открыть в браузере: http://localhost:5000/
6. Проверка: `python check.py`

Переменные окружения (файл `.env` не коммитится): `DATABASE_PATH`, `PORT`, `APP_VERSION`.

## Структура проекта
- `app.py` — приложение (API, веб-интерфейс, бизнес-правило).
- `schema.sql` — схема БД (5 таблиц, связи).
- `check.py` — локальные проверки.
- `Makefile` — команды: `make setup`, `make run`, `make test`, `make verify`.
- `docs/` — ТЗ, описание API, правила изменений, распределение ролей, git-процесс.
- `.env.example` — пример настроек без секретов.

## Сущности (вариант 8)
`groups` → `students`, `disciplines`, `study_plans` (учебный план группы), `grades`.
Бизнес-правило: оценку можно поставить только если дисциплина есть в учебном плане группы студента на этот семестр, оценка 2–5. Реализация — функция `check_business_rule` в `app.py`.

## Правила изменений (кратко, полный текст — в docs/RULES.md)
- Задача → ветка `feature/*` → коммиты → Pull Request → проверки → merge в `main`.
- Перед пушем выполнить `python check.py`.
- Запрещено коммитить `.env`, `*.db`, `__pycache__`, удалять проверки, пушить напрямую в `main`.

## Git-процесс
Ветка `feature/avg-report` → коммиты → PR → merge в `main` → разрешение конфликта (см. docs/GIT_PROCESS.md) → тег `v0.1.0`.
