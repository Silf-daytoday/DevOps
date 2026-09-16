# Описание API

База: `http://localhost:5000`. Все ответы — JSON. Ошибка — `{"error": "текст"}` + код 400/404.

| Метод | Адрес | Что делает | Пример |
|---|---|---|---|
| GET | `/health` | Жив ли сервер+БД | `{"status":"ok"}` |
| GET | `/version` | Версия | `{"version":"0.1.0"}` |
| GET | `/` | Веб-интерфейс (формы) | страница HTML |
| GET/POST | `/api/groups` | Список / создать `{name, year}` | `{"id":1}` |
| GET/POST | `/api/students` | Список / создать `{fio, group_id, student_no}` | `{"id":1}` |
| GET/POST | `/api/disciplines` | Список / создать `{name, credits}` | `{"id":1}` |
| GET/POST | `/api/plans` | Список / создать `{group_id, discipline_id, semester}` | `{"id":1}` |
| GET/POST | `/api/grades` | Список / создать `{student_id, discipline_id, semester, value}` | `{"id":1}` |
| GET | `/api/report/avg` | Средний балл | `[{"fio":"...","avg_score":4.5}]` |
| GET | `/api/docs` | Эта же справка в JSON | — |

Примеры (curl):
```
curl localhost:5000/health
curl -X POST localhost:5000/api/groups -H "Content-Type: application/json" -d "{\"name\":\"ИМ-31\",\"year\":2026}"
```
Порядок для демо: группа → студент → дисциплина → план → оценка → `/api/report/avg`.
При попытке поставить оценку без учебного плана возвращается 400 с сообщением о нарушении бизнес-правила.
