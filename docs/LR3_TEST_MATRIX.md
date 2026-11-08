# ЛР3: функции ТЗ и тесты

Покрытие кода и покрытие функций ТЗ — разные показатели.
База подсчёта — разделы 2–4 исторического docs/TZ.md:
20 CRUD-операций пяти сущностей, 4 операции аутентификации, 1 отчёт,
3 служебных адреса и 3 пункта ролевого разграничения.
Итого 31 функциональный пункт, из них 18 проверены: **58,1%**, больше 40%.
Границы и новая функция приведены отдельно и долю не увеличивают.
Метод подсчёта указан явно; пропущенное не считается проверенным.

| Пункты ТЗ | Проверено | Тесты |
|---|---|---|
| Группы: Create, Read | 2 из 4 CRUD | test_create_chain_through_api, test_empty_lists, test_web_create_and_escape |
| Студенты: Create, Read | 2 из 4 CRUD | те же; test_invalid_references_and_numbers |
| Дисциплины: Create, Read | 2 из 4 CRUD | test_create_chain_through_api, test_empty_lists |
| Учебные планы: Create, Read | 2 из 4 CRUD | test_create_chain_through_api, test_empty_lists |
| Оценки: Create, Read | 2 из 4 CRUD | test_create_chain_through_api, test_grade_boundaries, test_empty_lists |
| Регистрация, вход, выход, текущий пользователь | 4 из 4 | test_authentication, test_web_auth_roundtrip |
| Средний балл | 1 из 1 | test_average_numeric_and_null_last |
| health, version, api/docs | 3 из 3 | test_service_addresses, test_health_failure_redacts_password |
| Методист, преподаватель, студент: отдельные полномочия и только свои оценки | 0 из 3 | Полное разграничение не заявляется как проверенное |
| Update/Delete пяти предметных сущностей | 0 из 10, уже входят в CRUD выше | В текущем API отсутствуют |

Историческое ТЗ использует термин CRUD, но ЛР2 реализует GET/POST,
то есть создание и чтение. ЛР3 сохраняет это поведение. Анонимные
изменения через веб-формы перенаправляются на login; это проверено отдельно.

## Правила, ошибки и новая функция

- П1: оценка без плана запрещена — test_missing_plan, test_plan_required,
  test_web_errors_and_rollback; обход условия обнаруживается мутантом.
- П2: только 2–5 — test_allowed_grades/test_forbidden_grades,
  test_grade_boundaries/test_invalid_grade_values.
  Проверяются 1,2,5,6, bool, дробь, None, строка, список, объект.
- П3: дубликаты/связи — test_duplicates_and_rollback,
  test_invalid_references_and_numbers.
- Комментарий None/пустой/Unicode/500/501/неверный тип:
  test_comment/test_invalid_comment/test_comments/test_bad_comments.
- SQL CHECK комментария — test_database_comment_constraint.
- Экранирование HTML — test_web_create_and_escape.
- Числовой средний балл, NULL в конце — test_average_numeric_and_null_last.
- Rollback после ошибки — test_duplicates_and_rollback, test_web_errors_and_rollback.
- Ошибка health: 500, журнал без пароля, version доступен —
  test_health_failure_redacts_password.
- Идемпотентность admin — test_admin_idempotent/test_cli_init_admin и check.py.
- Ограничения инструментов — test_guards.py/test_backup_guards.py.
- Дрейф исходной схемы не допускает baseline — test_migration_guards.py.

## Проверки вне pytest

make migration-check: чистая БД; baseline заполненной ЛР2;
сохранение оценок; NULL для старых неизвестных дат; downgrade/upgrade.

make backup-check: pg_dump, изменение названия группы/оценки/комментария,
pg_restore, точное сравнение шести таблиц, вставка для проверки identity.

make mutation: два мутанта domain.py во временных копиях.
Каждый должен вызвать провал конкретного unit-теста; ошибка запуска pytest
не считается обнаружением мутанта. Рабочие исходники не изменяются.

check.py: сохранённая регрессия ЛР2, отдельно после make verify.
