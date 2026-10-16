# Описание API

Пример базы ЛР2 (адрес замените адресом своего app-server): `http://192.0.2.10:5000`. API возвращает JSON; `/` и страницы
аутентификации — HTML. Ошибка API — `{"error": "текст"}` + соответствующий код.

| Метод | Адрес | Что делает | Пример |
|---|---|---|---|
| GET | `/health` | SELECT 1 к БД: 200 при успехе, 500 при ошибке | `{"status":"ok"}` или `{"status":"fail"}` |
| GET | `/version` | Версия из APP_VERSION | `{"version":"0.2.0"}` |
| GET | `/` | Веб-интерфейс (формы) | страница HTML |
| GET/POST | `/api/groups` | Список / создать `{name, year}` | `{"id":1}` |
| GET/POST | `/api/students` | Список / создать `{fio, group_id, student_no}` | `{"id":1}` |
| GET/POST | `/api/disciplines` | Список / создать `{name, credits}` | `{"id":1}` |
| GET/POST | `/api/plans` | Список / создать `{group_id, discipline_id, semester}` | `{"id":1}` |
| GET/POST | `/api/grades` | Список / создать `{student_id, discipline_id, semester, value}` | `{"id":1}` |
| GET | `/api/report/avg` | Средний балл | `[{"fio":"...","avg_score":4.5}]` |
| POST | `/api/register` | Регистрация `{username, password}` | `{"id":1,"username":"..."}` |
| POST | `/api/login` | Вход `{username, password}` | `{"username":"..."}` |
| POST | `/api/logout` | Выход | `{"status":"ok"}` |
| GET | `/api/me` | Текущий пользователь (401 без входа) | `{"username":"..."}` |
| GET | `/api/docs` | Эта же справка в JSON | — |

Аутентификация: сессии на cookies. Веб-страницы `/register`, `/login`, `/logout`.
Изменение данных через веб-формы (`POST /web/*`) требует входа, без входа —
перенаправление на `/login`. Стартовый пользователь создаётся командой
`flask --app app init-admin` (служба вызывает её перед запуском): логин `admin`,
пароль из `ADMIN_PASSWORD`. Таблицы заранее создаются администратором.
Повторная инициализация не меняет пароль существующего admin.

При недоступной PostgreSQL `/health` не раскрывает внутреннюю ошибку и секреты;
тип ошибки записывается в журнал сервера. Подробные команды — в `docs/LR2.md`.

Примеры (curl):
```
curl localhost:5000/health
curl -X POST localhost:5000/api/groups -H "Content-Type: application/json" -d "{\"name\":\"ИМ-31\",\"year\":2026}"
```
Порядок для демо: группа → студент → дисциплина → план → оценка → `/api/report/avg`.
При попытке поставить оценку без учебного плана возвращается 400 с сообщением о нарушении бизнес-правила.
