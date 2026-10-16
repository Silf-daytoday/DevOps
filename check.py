"""Проверки приложения, только на отдельной PostgreSQL-базе devops_test."""
import os
import secrets

# Отказ ДО импорта приложения, подключения и тем более очистки.
if os.environ.get("DB_NAME") != "devops_test" or os.environ.get("DB_USER") != "devops_test":
    raise SystemExit("ОТКАЗ: проверки разрешены только с DB_NAME=devops_test и DB_USER=devops_test")

os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault("ADMIN_PASSWORD", secrets.token_urlsafe(24))

from app import app, init_db, get_db  # noqa: E402

app.config["TESTING"] = True
with app.app_context():
    db = get_db()
    identity = db.execute("SELECT current_database() AS db, current_user AS role").fetchone()
    if identity != {"db": "devops_test", "role": "devops_test"}:
        raise SystemExit("ОТКАЗ: фактические база/пользователь не соответствуют тестовому окружению")
    db.execute("TRUNCATE groups, students, disciplines, study_plans, grades, users RESTART IDENTITY")
    db.commit()
    init_db()
c = app.test_client()

fails = []


def check(name, cond):
    print(("OK  " if cond else "FAIL") + " " + name)
    if not cond:
        fails.append(name)


# Повторная инициализация не должна менять пароль уже созданного admin.
with app.app_context():
    before = get_db().execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
    init_db()
    after = get_db().execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
check("Повторный init-admin сохраняет пароль", before == after)


# health + version
r = c.get("/health")
check("GET /health -> 200 ok", r.status_code == 200 and r.get_json()["status"] == "ok")
r = c.get("/version")
check("GET /version", r.status_code == 200 and "version" in r.get_json())

# Создание цепочки: группа -> студент, дисциплина -> план -> оценка
g = c.post("/api/groups", json={"name": "ИМ-31", "year": 2026})
check("POST /api/groups", g.status_code == 201)
gid = g.get_json()["id"]

s = c.post("/api/students", json={"fio": "Иванов И.И.", "group_id": gid, "student_no": "Z-001"})
check("POST /api/students", s.status_code == 201)
sid = s.get_json()["id"]

d = c.post("/api/disciplines", json={"name": "DevOps", "credits": 3})
check("POST /api/disciplines", d.status_code == 201)
did = d.get_json()["id"]

# Ошибка: оценка без учебного плана должна отклониться (бизнес-правило!)
bad = c.post("/api/grades",
             json={"student_id": sid, "discipline_id": did, "semester": 5, "value": 5})
check("Бизнес-правило: оценка без плана отклонена",
      bad.status_code == 400 and "учебн" in bad.get_json()["error"].lower())

p = c.post("/api/plans", json={"group_id": gid, "discipline_id": did, "semester": 5})
check("POST /api/plans", p.status_code == 201)

good = c.post("/api/grades",
              json={"student_id": sid, "discipline_id": did, "semester": 5, "value": 5})
check("Оценка с планом принята", good.status_code == 201)

# Ошибка: оценка 10 невозможна
bad2 = c.post("/api/grades",
              json={"student_id": sid, "discipline_id": did, "semester": 5, "value": 10})
check("Оценка 10 отклонена", bad2.status_code == 400)

# Ошибка: мусор вместо чисел
bad3 = c.post("/api/groups", json={"name": "X"})
check("Нет year -> 400", bad3.status_code == 400)

# Отчёт средний балл
rep = c.get("/api/report/avg")
check("GET /api/report/avg", rep.status_code == 200 and rep.get_json()[0]["avg_score"] == 5.0)

# Веб-страница открывается
w = c.get("/")
check("GET / (веб-интерфейс)", w.status_code == 200 and "Успеваемость" in w.get_data(as_text=True))

# --- Аутентификация ---
r = c.post("/api/register", json={"username": "t", "password": "pw"})
check("Короткий логин/пароль отклонены", r.status_code == 400)

r = c.post("/api/register", json={"username": "teacher1", "password": "pass123"})
check("POST /api/register", r.status_code == 201)

r = c.post("/api/register", json={"username": "teacher1", "password": "pass123"})
check("Повторная регистрация отклонена", r.status_code == 400)

r = c.post("/api/login", json={"username": "teacher1", "password": "wrong"})
check("Неверный пароль отклонён", r.status_code == 401)

r = c.post("/api/login", json={"username": "teacher1", "password": "pass123"})
check("POST /api/login", r.status_code == 200)

me = c.get("/api/me")
check("GET /api/me после входа", me.status_code == 200 and me.get_json()["username"] == "teacher1")

# Без входа изменение через веб-форму запрещено
anon = app.test_client()
anon.get("/")  # отдельная сессия без входа
r = anon.post("/web/groups", data={"name": "X-1", "year": "2026"})
check("Веб-форма без входа ведёт на /login", r.status_code == 302 and "/login" in r.headers["Location"])

# Со входом веб-форма работает
r = c.post("/web/groups", data={"name": "ИМ-32", "year": "2026"})
check("Веб-форма со входом работает", r.status_code == 302)

# В PostgreSQL после IntegrityError нужен rollback перед current_user() в page().
r = c.post("/web/groups", data={"name": "ИМ-32", "year": "2026"})
check("Дубликат в веб-форме -> 400, транзакция восстановлена", r.status_code == 400)
check("БД доступна после дубликата", c.get("/").status_code == 200)
r = c.post("/web/groups", data={"name": "X", "year": "not-a-number"})
check("Нечисловое поле веб-формы -> 400", r.status_code == 400)

for path, payload in (
    ("/api/students", {"fio": "X", "group_id": "bad", "student_no": "X"}),
    ("/api/disciplines", {"name": "X", "credits": "bad"}),
    ("/api/groups", [1, 2]),
):
    check(f"Некорректный ввод {path} -> 400", c.post(path, json=payload).status_code == 400)

student_without_grades = c.post("/api/students", json={
    "fio": "Без оценок", "group_id": gid, "student_no": "Z-002",
})
check("Студент без оценок создан", student_without_grades.status_code == 201)
report = c.get("/api/report/avg").get_json()
check("Средний балл — число, без оценок — NULL в конце",
      report[0]["id"] == sid and isinstance(report[0]["avg_score"], (int, float))
      and report[-1]["avg_score"] is None)

r = c.post("/api/logout")
check("POST /api/logout", r.status_code == 200)
me = c.get("/api/me")
check("GET /api/me после выхода -> 401", me.status_code == 401)

print()
if fails:
    print(f"ИТОГ: {len(fails)} провалов: {fails}")
    raise SystemExit(1)
print("ИТОГ: все проверки прошли.")
