"""Локальная проверка для ЛР1: гоняет API и бизнес-правило. Запуск: python check.py"""
import os
import tempfile

os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), "lr1_check.db")
try:
    os.remove(os.environ["DATABASE_PATH"])
except FileNotFoundError:
    pass

from app import app, init_db  # noqa: E402

app.config["TESTING"] = True
with app.app_context():
    init_db()
c = app.test_client()

fails = []


def check(name, cond):
    print(("OK  " if cond else "FAIL") + " " + name)
    if not cond:
        fails.append(name)


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

r = c.post("/api/logout")
check("POST /api/logout", r.status_code == 200)
me = c.get("/api/me")
check("GET /api/me после выхода -> 401", me.status_code == 401)

print()
if fails:
    print(f"ИТОГ: {len(fails)} провалов: {fails}")
    raise SystemExit(1)
print("ИТОГ: все проверки прошли.")
