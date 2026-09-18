"""Учёт успеваемости студентов. Вариант 8. ЛР1.
Сущности: groups -> students, disciplines, study_plans, grades, users.
Бизнес-правило: оценка выставляется только если дисциплина
включена в учебный план группы студента на указанный семестр (оценка 2–5).
Аутентификация: регистрация и вход по логину/паролю (пароли хранятся
только в виде хеша). Изменение данных через веб-формы требует входа.
"""
import html
import os
import sqlite3
from functools import wraps

from flask import Flask, request, jsonify, g, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

# --- Конфигурация через переменные окружения ---
DB_PATH = os.environ.get("DATABASE_PATH", "data/app.db")
PORT = int(os.environ.get("PORT", "5000"))
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

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
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'teacher'
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
    # Стартовый администратор (логин: admin, пароль из ADMIN_PASSWORD).
    row = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not row:
        db.execute(
            "INSERT INTO users(username, password_hash, role) VALUES(?,?,?)",
            ("admin", generate_password_hash(ADMIN_PASSWORD), "admin"),
        )
    db.commit()


def esc(value):
    """Экранирование для безопасного вывода в HTML."""
    return html.escape("" if value is None else str(value))


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute("SELECT id, username, role FROM users WHERE id=?", (uid,)).fetchone()


def login_required(view):
    """Изменение данных доступно только вошедшим пользователям."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify({"error": "Требуется вход"}), 401
            return redirect(url_for("login_page", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# --- Служебные адреса ---
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


# --- Стили и шаблоны страниц ---
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#eef1f6;color:#1f2937;min-height:100vh}
.topbar{background:linear-gradient(90deg,#1e3a8a,#3b82f6);color:#fff;padding:14px 28px;
display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.topbar .logo{font-size:20px;font-weight:700}
.topbar nav a{color:#dbeafe;text-decoration:none;margin:0 10px;font-size:14px}
.topbar nav a:hover{color:#fff;text-decoration:underline}
.topbar .user{font-size:14px}
.topbar .user a{color:#fff;font-weight:600}
.btn{display:inline-block;background:#2563eb;color:#fff!important;border:none;border-radius:8px;
padding:9px 18px;font-size:14px;cursor:pointer;text-decoration:none}
.btn:hover{background:#1d4ed8}
.btn-light{background:#e0e7ff;color:#1e3a8a!important}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
.hero{background:#fff;border-radius:14px;padding:26px 30px;margin-bottom:22px;
box-shadow:0 2px 10px rgba(0,0,0,.06);border-left:6px solid #2563eb}
.hero h1{font-size:24px;margin-bottom:6px}
.hero p{color:#6b7280;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:22px}
.card{background:#fff;border-radius:14px;padding:20px;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.card h2{font-size:16px;margin-bottom:12px;color:#1e3a8a}
.card label{display:block;font-size:12px;color:#6b7280;margin:8px 0 3px}
.card input,.card select{width:100%;padding:9px 10px;border:1px solid #d1d5db;border-radius:8px;font-size:14px}
.card input:focus,.card select:focus{outline:none;border-color:#2563eb;box-shadow:0 0 0 2px #bfdbfe}
.card .btn{margin-top:12px;width:100%}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:14px;overflow:hidden;
box-shadow:0 2px 10px rgba(0,0,0,.06);font-size:14px}
th{background:#1e3a8a;color:#fff;text-align:left;padding:11px 14px}
td{padding:10px 14px;border-top:1px solid #e5e7eb}
tr:nth-child(even) td{background:#f8fafc}
.section-title{font-size:18px;margin:22px 0 10px}
.badge{display:inline-block;min-width:30px;text-align:center;padding:3px 10px;border-radius:20px;
color:#fff;font-weight:700}
.b5{background:#16a34a}.b4{background:#2563eb}.b3{background:#f59e0b}.b2{background:#dc2626}
.bar{height:8px;background:#e5e7eb;border-radius:6px;overflow:hidden;min-width:90px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#3b82f6,#16a34a)}
.notice{background:#fef3c7;border:1px solid #f59e0b;border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:14px}
.error{background:#fee2e2;border:1px solid #dc2626;border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:14px}
.auth-box{max-width:420px;margin:60px auto;background:#fff;border-radius:14px;padding:30px;
box-shadow:0 4px 20px rgba(0,0,0,.1)}
.auth-box h1{font-size:20px;margin-bottom:16px;color:#1e3a8a}
.footer{text-align:center;color:#9ca3af;font-size:12px;padding:24px}
"""

BASE_TOP = """<html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{title}</title><style>{css}</style></head><body>
<div class='topbar'><div class='logo'>📚 Успеваемость · Вар. 8</div>
<nav><a href='/'>Главная</a><a href='/api/docs'>API</a><a href='/health'>Health</a><a href='/version'>Version</a></nav>
<div class='user'>{auth}</div></div><div class='wrap'>"""


def page(title, body):
    user = current_user()
    if user:
        auth = f"{esc(user['username'])} ({esc(user['role'])}) · <a href='/logout'>Выйти</a>"
    else:
        auth = "<a href='/login'>Войти</a> · <a href='/register'>Регистрация</a>"
    return (BASE_TOP.format(title=esc(title), css=CSS, auth=auth)
            + body + "</div><div class='footer'>ЛР1 · Вариант 8 · Учёт успеваемости студентов</div></body></html>")


def grade_badge(value):
    return f"<span class='badge b{value}'>{value}</span>"


# --- Главная страница ---
@app.get("/")
def index():
    db = get_db()
    groups = db.execute("SELECT * FROM groups ORDER BY name").fetchall()
    students = db.execute(
        "SELECT s.*, gr.name as group_name FROM students s JOIN groups gr ON gr.id=s.group_id"
    ).fetchall()
    disciplines = db.execute("SELECT * FROM disciplines ORDER BY name").fetchall()
    grades = db.execute(
        """SELECT gr.value, gr.semester, s.fio, d.name as disc
           FROM grades gr JOIN students s ON s.id=gr.student_id
           JOIN disciplines d ON d.id=gr.discipline_id ORDER BY gr.id DESC LIMIT 50"""
    ).fetchall()
    avg = db.execute(
        """SELECT s.fio, ROUND(AVG(gr.value),2) as avg_score, COUNT(gr.id) as cnt
           FROM students s LEFT JOIN grades gr ON gr.student_id=s.id
           GROUP BY s.id ORDER BY avg_score DESC"""
    ).fetchall()

    user = current_user()
    notice = ""
    if not user:
        notice = ("<div class='notice'>Вы не вошли в систему: просмотр открыт для всех, "
                  "а добавление данных требует входа. <a href='/login'>Войти</a> · "
                  "демо-логин <b>admin</b>.</div>")

    rows_avg = "".join(
        "<tr><td>{fio}</td><td>{score}</td>"
        "<td><div class='bar'><i style='width:{w}%'></i></div></td>"
        "<td>{cnt}</td></tr>".format(
            fio=esc(r["fio"]),
            score=r["avg_score"] or "—",
            w=int((r["avg_score"] or 0) / 5 * 100),
            cnt=r["cnt"],
        ) for r in avg
    ) or "<tr><td colspan=4>Пока нет студентов</td></tr>"
    rows_gr = "".join(
        "<tr><td>{fio}</td><td>{d}</td><td>Семестр {s}</td><td>{b}</td></tr>".format(
            fio=esc(r["fio"]), d=esc(r["disc"]), s=r["semester"],
            b=grade_badge(r["value"]),
        ) for r in grades
    ) or "<tr><td colspan=4>Оценок пока нет</td></tr>"
    opt_g = "".join(f"<option value='{r['id']}'>{esc(r['name'])}</option>" for r in groups)
    opt_s = "".join(f"<option value='{r['id']}'>{esc(r['fio'])}</option>" for r in students)
    opt_d = "".join(f"<option value='{r['id']}'>{esc(r['name'])}</option>" for r in disciplines)

    body = f"""
<div class='hero'><h1>Учёт успеваемости студентов</h1>
<p>Группы · студенты · дисциплины · учебные планы · оценки. Средний балл считается автоматически.</p></div>
{notice}
<div class='grid'>
<div class='card'><h2>➕ Группа</h2>
<form method='post' action='/web/groups'>
<label>Название</label><input name='name' placeholder='ИМ-31' required>
<label>Год набора</label><input name='year' placeholder='2026' required>
<button class='btn'>Добавить</button></form></div>
<div class='card'><h2>🧑 Студент</h2>
<form method='post' action='/web/students'>
<label>ФИО</label><input name='fio' placeholder='Иванов И.И.' required>
<label>Номер зачётки</label><input name='student_no' placeholder='Z-001' required>
<label>Группа</label><select name='group_id'>{opt_g}</select>
<button class='btn'>Добавить</button></form></div>
<div class='card'><h2>📖 Дисциплина</h2>
<form method='post' action='/web/disciplines'>
<label>Название</label><input name='name' placeholder='DevOps' required>
<label>Кредиты</label><input name='credits' placeholder='3'>
<button class='btn'>Добавить</button></form></div>
<div class='card'><h2>🗂 В учебный план</h2>
<form method='post' action='/web/plans'>
<label>Группа</label><select name='group_id'>{opt_g}</select>
<label>Дисциплина</label><select name='discipline_id'>{opt_d}</select>
<label>Семестр</label><input name='semester' placeholder='5' required>
<button class='btn'>В план</button></form></div>
<div class='card'><h2>⭐ Поставить оценку</h2>
<form method='post' action='/web/grades'>
<label>Студент</label><select name='student_id'>{opt_s}</select>
<label>Дисциплина</label><select name='discipline_id'>{opt_d}</select>
<label>Семестр</label><input name='semester' placeholder='5' required>
<label>Оценка (2–5)</label><input name='value' placeholder='5' required>
<button class='btn'>Оценить</button></form></div>
</div>
<div class='section-title'>Последние оценки</div>
<table><tr><th>Студент</th><th>Дисциплина</th><th>Семестр</th><th>Оценка</th></tr>{rows_gr}</table>
<div class='section-title'>Средний балл</div>
<table><tr><th>Студент</th><th>Балл</th><th>Прогресс</th><th>Оценок</th></tr>{rows_avg}</table>
"""
    return page("Успеваемость — Вариант 8", body)


# --- Регистрация / вход / выход (веб) ---
def auth_form(title, action, error=""):
    err = f"<div class='error'>{esc(error)}</div>" if error else ""
    return page(title, f"""<div class='auth-box'><h1>{esc(title)}</h1>{err}
<form method='post' action='{action}'>
<div class='card' style='box-shadow:none;padding:0'>
<label>Логин</label><input name='username' required minlength='3'>
<label>Пароль</label><input name='password' type='password' required minlength='4'>
<button class='btn'>Продолжить</button></div></form></div>""")


@app.get("/register")
def register_page():
    if current_user():
        return redirect(url_for("index"))
    return auth_form("Регистрация", "/register")


@app.post("/register")
def register_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if len(username) < 3 or len(password) < 4:
        return auth_form("Регистрация", "/register", "Логин — от 3 символов, пароль — от 4"), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users(username, password_hash) VALUES(?,?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return auth_form("Регистрация", "/register", "Такой логин уже занят"), 400
    session["user_id"] = cur.lastrowid
    return redirect(url_for("index"))


@app.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("index"))
    return auth_form("Вход", "/login")


@app.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    row = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return auth_form("Вход", "/login", "Неверный логин или пароль"), 401
    session["user_id"] = row["id"]
    return redirect(request.args.get("next") or url_for("index"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# --- Веб-формы изменения данных (только для вошедших) ---
@app.post("/web/groups")
@login_required
def web_add_group():
    return _web_create("INSERT INTO groups(name,year) VALUES(?,?)",
                       (request.form["name"], int(request.form["year"])))


@app.post("/web/students")
@login_required
def web_add_student():
    return _web_create(
        "INSERT INTO students(fio,group_id,student_no) VALUES(?,?,?)",
        (request.form["fio"], int(request.form["group_id"]), request.form["student_no"]),
    )


@app.post("/web/disciplines")
@login_required
def web_add_disc():
    return _web_create("INSERT INTO disciplines(name,credits) VALUES(?,?)",
                       (request.form["name"], int(request.form.get("credits") or 3)))


@app.post("/web/plans")
@login_required
def web_add_plan():
    return _web_create(
        "INSERT INTO study_plans(group_id,discipline_id,semester) VALUES(?,?,?)",
        (int(request.form["group_id"]), int(request.form["discipline_id"]),
         int(request.form["semester"])),
    )


@app.post("/web/grades")
@login_required
def web_add_grade():
    err = check_business_rule(
        int(request.form["student_id"]), int(request.form["discipline_id"]),
        int(request.form["semester"]), int(request.form["value"]),
    )
    if err:
        return page("Ошибка", f"<div class='error'>{esc(err)}</div><a class='btn' href='/'>Назад</a>"), 400
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
        return page("Ошибка",
                    f"<div class='error'>Такая запись уже есть ({esc(e)})</div>"
                    "<a class='btn' href='/'>Назад</a>"), 400
    return redirect(url_for("index"))


# --- Бизнес-правило ---
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
        "POST /api/register": "регистрация {username, password}",
        "POST /api/login": "вход {username, password}",
        "POST /api/logout": "выход",
        "GET /api/me": "текущий пользователь",
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


# --- Аутентификация через API ---
@app.post("/api/register")
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    username, password = (data.get("username") or "").strip(), data.get("password") or ""
    if len(username) < 3 or len(password) < 4:
        return jsonify({"error": "Логин — от 3 символов, пароль — от 4"}), 400
    try:
        db = get_db()
        cur = db.execute(
            "INSERT INTO users(username, password_hash) VALUES(?,?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Такой логин уже занят"}), 400
    session["user_id"] = cur.lastrowid
    return jsonify({"id": cur.lastrowid, "username": username}), 201


@app.post("/api/login")
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    username, password = (data.get("username") or "").strip(), data.get("password") or ""
    row = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Неверный логин или пароль"}), 401
    session["user_id"] = row["id"]
    return jsonify({"id": row["id"], "username": row["username"], "role": row["role"]})


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})


@app.get("/api/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"error": "Требуется вход"}), 401
    return jsonify({"id": user["id"], "username": user["username"], "role": user["role"]})


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
