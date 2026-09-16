"""Учёт успеваемости студентов. Вариант 8. ЛР1.
Сущности: groups -> students, disciplines, study_plans, grades.
Бизнес-правило: оценка выставляется только если дисциплина
включена в учебный план группы студента на указанный семестр (оценка 2–5).
"""
import os
import sqlite3
from flask import Flask, request, jsonify, g, redirect, url_for

# --- Конфигурация через переменные окружения (требование ЛР1 п.6) ---
DB_PATH = os.environ.get("DATABASE_PATH", "data/app.db")
PORT = int(os.environ.get("PORT", "5000"))
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")

app = Flask(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    year INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fio TEXT NOT NULL,
    group_id INTEGER NOT NULL REFERENCES groups(id),
    student_no TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS disciplines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    credits INTEGER NOT NULL DEFAULT 3
);
CREATE TABLE IF NOT EXISTS study_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES groups(id),
    discipline_id INTEGER NOT NULL REFERENCES disciplines(id),
    semester INTEGER NOT NULL,
    UNIQUE(group_id, discipline_id, semester)
);
CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    discipline_id INTEGER NOT NULL REFERENCES disciplines(id),
    semester INTEGER NOT NULL,
    value INTEGER NOT NULL CHECK(value BETWEEN 2 AND 5),
    UNIQUE(student_id, discipline_id, semester)
);
"""


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


# --- Служебные адреса (требование ЛР1 п.6) ---
@app.get("/health")
def health():
    try:
        db = get_db()
        db.execute("SELECT 1").fetchone()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500


@app.get("/version")
def version():
    return jsonify({"version": APP_VERSION})


# --- Главная: веб-интерфейс (требование: веб-интерфейс обязателен) ---
@app.get("/")
def index():
    db = get_db()
    groups = db.execute("SELECT * FROM groups").fetchall()
    students = db.execute(
        "SELECT s.*, gr.name as group_name FROM students s JOIN groups gr ON gr.id=s.group_id"
    ).fetchall()
    disciplines = db.execute("SELECT * FROM disciplines").fetchall()
    grades = db.execute(
        """SELECT gr.value, gr.semester, s.fio, d.name as disc
           FROM grades gr JOIN students s ON s.id=gr.student_id
           JOIN disciplines d ON d.id=gr.discipline_id ORDER BY gr.id DESC LIMIT 50"""
    ).fetchall()
    # Средний балл по студентам (отчёт для варианта 8)
    avg = db.execute(
        """SELECT s.fio, ROUND(AVG(gr.value),2) as avg_score, COUNT(gr.id) as cnt
           FROM students s LEFT JOIN grades gr ON gr.student_id=s.id
           GROUP BY s.id ORDER BY avg_score DESC"""
    ).fetchall()

    rows_avg = "".join(
        f"<tr><td>{r['fio']}</td><td>{r['avg_score'] or '-'}</td><td>{r['cnt']}</td></tr>" for r in avg
    )
    rows_gr = "".join(
        f"<tr><td>{r['fio']}</td><td>{r['disc']}</td><td>{r['semester']}</td><td>{r['value']}</td></tr>"
        for r in grades
    )
    opt_g = "".join(f"<option value='{r['id']}'>{r['name']}</option>" for r in groups)
    opt_s = "".join(f"<option value='{r['id']}'>{r['fio']}</option>" for r in students)
    opt_d = "".join(f"<option value='{r['id']}'>{r['name']}</option>" for r in disciplines)
    return f"""<html><head><meta charset='utf-8'><title>Успеваемость (Вар.8)</title></head>
<body style='font-family:sans-serif;max-width:900px;margin:auto'>
<h1>Учёт успеваемости студентов — Вариант 8</h1>
<p><a href='/health'>/health</a> | <a href='/version'>/version</a> | <a href='/api/docs'>Описание API</a></p>
<h2>Добавить группу</h2>
<form method='post' action='/web/groups'><input name='name' placeholder='ИМ-31' required>
<input name='year' placeholder='2026' required><button>Добавить</button></form>
<h2>Добавить студента</h2>
<form method='post' action='/web/students'><input name='fio' placeholder='Иванов И.И.' required>
<input name='student_no' placeholder='Номер зачётки' required>
<select name='group_id'>{opt_g}</select><button>Добавить</button></form>
<h2>Добавить дисциплину</h2>
<form method='post' action='/web/disciplines'><input name='name' placeholder='DevOps' required>
<input name='credits' placeholder='3'><button>Добавить</button></form>
<h2>В учебный план</h2>
<form method='post' action='/web/plans'>Группа:<select name='group_id'>{opt_g}</select>
Дисциплина:<select name='discipline_id'>{opt_d}</select>
<input name='semester' placeholder='Семестр, напр. 5' required><button>В план</button></form>
<h2>Поставить оценку (с проверкой учебного плана!)</h2>
<form method='post' action='/web/grades'>Студент:<select name='student_id'>{opt_s}</select>
Дисциплина:<select name='discipline_id'>{opt_d}</select>
<input name='semester' placeholder='Семестр' required>
<input name='value' placeholder='2-5' required><button>Оценить</button></form>
<h2>Последние оценки</h2>
<table border=1><tr><th>Студент</th><th>Дисциплина</th><th>Семестр</th><th>Оценка</th></tr>{rows_gr}</table>
<h2>Средний балл (отчёт)</h2>
<table border=1><tr><th>Студент</th><th>Средний балл</th><th>Кол-во оценок</th></tr>{rows_avg}</table>
</body></html>"""


# --- Веб-формы (чтобы удобно показывать на защите) ---
@app.post("/web/groups")
def web_add_group():
    return _web_create("INSERT INTO groups(name,year) VALUES(?,?)",
                       (request.form["name"], int(request.form["year"])))


@app.post("/web/students")
def web_add_student():
    return _web_create(
        "INSERT INTO students(fio,group_id,student_no) VALUES(?,?,?)",
        (request.form["fio"], int(request.form["group_id"]), request.form["student_no"]),
    )


@app.post("/web/disciplines")
def web_add_disc():
    return _web_create("INSERT INTO disciplines(name,credits) VALUES(?,?)",
                       (request.form["name"], int(request.form.get("credits") or 3)))


@app.post("/web/plans")
def web_add_plan():
    return _web_create(
        "INSERT INTO study_plans(group_id,discipline_id,semester) VALUES(?,?,?)",
        (int(request.form["group_id"]), int(request.form["discipline_id"]),
         int(request.form["semester"])),
    )


@app.post("/web/grades")
def web_add_grade():
    err = check_business_rule(
        int(request.form["student_id"]), int(request.form["discipline_id"]),
        int(request.form["semester"]), int(request.form["value"]),
    )
    if err:
        return f"<h3>Ошибка: {err}</h3><a href='/'>Назад</a>", 400
    return _web_create(
        "INSERT INTO grades(student_id,discipline_id,semester,value) VALUES(?,?,?,?)",
        (int(request.form["student_id"]), int(request.form["discipline_id"]),
         int(request.form["semester"]), int(request.form["value"])),
    )


def _web_create(sql, params):
    db = get_db()
    try:
        db.execute(sql, params)
        db.commit()
    except sqlite3.IntegrityError as e:
        return f"<h3>Ошибка: такая запись уже есть ({e})</h3><a href='/'>Назад</a>", 400
    return redirect(url_for("index"))


# --- БИЗНЕС-ПРАВИЛО (самое важное для защиты!) ---
def check_business_rule(student_id, discipline_id, semester, value):
    """Возвращает текст ошибки или None если всё ок."""
    if value not in (2, 3, 4, 5):
        return "Оценка должна быть от 2 до 5"
    db = get_db()
    st = db.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if not st:
        return "Такого студента нет"
    plan = db.execute(
        "SELECT * FROM study_plans WHERE group_id=? AND discipline_id=? AND semester=?",
        (st["group_id"], discipline_id, semester),
    ).fetchone()
    if not plan:
        return ("Нельзя ставить оценку: этой дисциплины НЕТ в учебном плане "
                "группы студента на этот семестр")
    return None


# --- HTTP API (JSON) ---
@app.get("/api/docs")
def api_docs():
    return jsonify({
        "GET /health": "проверка работоспособности",
        "GET /version": "версия приложения",
        "GET/POST /api/groups": "список/создание групп",
        "GET/POST /api/students": "список/создание студентов",
        "GET/POST /api/disciplines": "список/создание дисциплин",
        "GET/POST /api/plans": "учебные планы",
        "GET/POST /api/grades": "оценки (с проверкой бизнес-правила)",
        "GET /api/report/avg": "средний балл по студентам",
    })


def _list(sql):
    return jsonify([dict(r) for r in get_db().execute(sql).fetchall()])


@app.get("/api/groups")
def api_groups():
    return _list("SELECT * FROM groups")


@app.post("/api/groups")
def api_add_group():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("name") or "year" not in data:
        return jsonify({"error": "Нужно name и year"}), 400
    try:
        db = get_db()
        cur = db.execute("INSERT INTO groups(name,year) VALUES(?,?)",
                         (data["name"], int(data["year"])))
        db.commit()
        return jsonify({"id": cur.lastrowid}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Такая группа уже есть"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "year должен быть числом"}), 400


@app.get("/api/students")
def api_students():
    return _list("SELECT * FROM students")


@app.post("/api/students")
def api_add_student():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("fio") or not data.get("group_id") or not data.get("student_no"):
        return jsonify({"error": "Нужно fio, group_id, student_no"}), 400
    try:
        db = get_db()
        if not db.execute("SELECT 1 FROM groups WHERE id=?",
                          (int(data["group_id"]),)).fetchone():
            return jsonify({"error": "Такой группы нет"}), 400
        cur = db.execute("INSERT INTO students(fio,group_id,student_no) VALUES(?,?,?)",
                         (data["fio"], int(data["group_id"]), data["student_no"]))
        db.commit()
        return jsonify({"id": cur.lastrowid}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Такой номер зачётки уже есть"}), 400


@app.get("/api/disciplines")
def api_discs():
    return _list("SELECT * FROM disciplines")


@app.post("/api/disciplines")
def api_add_disc():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Нужно name"}), 400
    try:
        db = get_db()
        cur = db.execute("INSERT INTO disciplines(name,credits) VALUES(?,?)",
                         (data["name"], int(data.get("credits", 3))))
        db.commit()
        return jsonify({"id": cur.lastrowid}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Такая дисциплина уже есть"}), 400


@app.get("/api/plans")
def api_plans():
    return _list("SELECT * FROM study_plans")


@app.post("/api/plans")
def api_add_plan():
    data = request.get_json(force=True, silent=True) or {}
    try:
        gid, did, sem = int(data["group_id"]), int(data["discipline_id"]), int(data["semester"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Нужно group_id, discipline_id, semester (числа)"}), 400
    try:
        db = get_db()
        cur = db.execute(
            "INSERT INTO study_plans(group_id,discipline_id,semester) VALUES(?,?,?)",
            (gid, did, sem))
        db.commit()
        return jsonify({"id": cur.lastrowid}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Такой план уже есть или нет группы/дисциплины"}), 400


@app.get("/api/grades")
def api_grades():
    return _list("SELECT * FROM grades")


@app.post("/api/grades")
def api_add_grade():
    data = request.get_json(force=True, silent=True) or {}
    try:
        sid, did, sem, val = (int(data["student_id"]), int(data["discipline_id"]),
                              int(data["semester"]), int(data["value"]))
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Нужно student_id, discipline_id, semester, value (числа)"}), 400
    err = check_business_rule(sid, did, sem, val)
    if err:
        return jsonify({"error": err}), 400
    try:
        db = get_db()
        cur = db.execute(
            "INSERT INTO grades(student_id,discipline_id,semester,value) VALUES(?,?,?,?)",
            (sid, did, sem, val))
        db.commit()
        return jsonify({"id": cur.lastrowid}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Такая оценка уже стоит"}), 400


@app.get("/api/report/avg")
def api_avg():
    rows = get_db().execute(
        """SELECT s.id, s.fio, ROUND(AVG(g.value),2) as avg_score, COUNT(g.id) as cnt
           FROM students s LEFT JOIN grades g ON g.student_id=s.id
           GROUP BY s.id ORDER BY avg_score DESC"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.errorhandler(404)
def nf(e):
    return jsonify({"error": "Не найдено. Смотри /api/docs"}), 404


@app.errorhandler(405)
def nm(e):
    return jsonify({"error": "Метод не разрешён"}), 405


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=PORT)

# feature avg-report commit1
# feature avg-report commit2
