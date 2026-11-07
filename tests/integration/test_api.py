import os
import secrets

import psycopg
import pytest

pytestmark = pytest.mark.integration


def grade(chain, **changes):
    return dict(
        student_id=chain["student"],
        discipline_id=chain["discipline"],
        semester=5,
        value=5,
        **changes,
    )


def test_service_addresses(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    assert client.get("/health").status_code == 200
    assert "version" in client.get("/version").get_json()
    assert client.get("/api/docs").is_json
    assert client.get("/missing").status_code == 404
    assert client.delete("/api/groups").status_code == 405


@pytest.mark.parametrize("resource", ["groups", "students", "disciplines", "plans", "grades"])
def test_empty_lists(client, resource):
    assert client.get(f"/api/{resource}").get_json() == []


def test_create_chain_through_api(client):
    response = client.post("/api/groups", json={"name": "API-GROUP", "year": 2026})
    assert response.status_code == 201
    gid = response.get_json()["id"]
    response = client.post(
        "/api/students", json={"fio": "API Student", "group_id": gid, "student_no": "API-001"}
    )
    assert response.status_code == 201
    sid = response.get_json()["id"]
    response = client.post("/api/disciplines", json={"name": "API Discipline"})
    assert response.status_code == 201
    did = response.get_json()["id"]
    response = client.post(
        "/api/plans", json={"group_id": gid, "discipline_id": did, "semester": 5}
    )
    assert response.status_code == 201
    response = client.post(
        "/api/grades",
        json={
            "student_id": sid,
            "discipline_id": did,
            "semester": 5,
            "value": 4,
            "comment": "Проверено",
        },
    )
    assert response.status_code == 201
    row = client.get("/api/grades").get_json()[0]
    assert row["comment"] == "Проверено" and row["created_at"]
    assert client.get("/api/students").get_json()[0]["fio"] == "API Student"
    assert client.get("/api/disciplines").get_json()[0]["credits"] == 3
    assert len(client.get("/api/plans").get_json()) == 1


@pytest.mark.parametrize("value", [2, 3, 4, 5])
def test_grade_boundaries(client, chain, value):
    payload = grade(chain)
    payload["value"] = value
    assert client.post("/api/grades", json=payload).status_code == 201


@pytest.mark.parametrize("value", [1, 6, 10, -1, True, 2.5, "2.5", None, [], {}])
def test_invalid_grade_values(client, chain, value):
    payload = grade(chain)
    payload["value"] = value
    assert client.post("/api/grades", json=payload).status_code == 400
    assert client.get("/api/grades").get_json() == []


def test_plan_required(client, chain, db):
    db.execute("DELETE FROM study_plans")
    db.commit()
    response = client.post("/api/grades", json=grade(chain))
    assert response.status_code == 400
    assert "учебном плане" in response.get_json()["error"]
    assert client.get("/api/grades").get_json() == []


def test_student_required(client, chain):
    payload = grade(chain)
    payload["student_id"] = 999999
    response = client.post("/api/grades", json=payload)
    assert response.status_code == 400
    assert "студента нет" in response.get_json()["error"]


@pytest.mark.parametrize("comment", [None, "", " текст ", "я" * 500, "<script>alert(1)</script>"])
def test_comments(client, chain, comment):
    assert client.post("/api/grades", json=grade(chain, comment=comment)).status_code == 201
    row = client.get("/api/grades").get_json()[0]
    assert row["comment"] == (comment.strip() or None if comment is not None else None)


@pytest.mark.parametrize("comment", ["я" * 501, " " * 501, 5, [], {}, True])
def test_bad_comments(client, chain, comment):
    response = client.post("/api/grades", json=grade(chain, comment=comment))
    assert response.status_code == 400
    assert "Комментарий" in response.get_json()["error"]
    assert client.get("/api/grades").get_json() == []


@pytest.mark.parametrize(
    "resource", ["groups", "students", "disciplines", "plans", "grades", "register"]
)
@pytest.mark.parametrize("payload", [[], None, {}, {"year": "bad"}])
def test_malformed_requests(client, resource, payload):
    assert client.post(f"/api/{resource}", json=payload).status_code == 400


def test_duplicates_and_rollback(client, chain):
    requests = [
        ("/api/groups", {"name": "TEST-GROUP", "year": 2026}),
        (
            "/api/students",
            {"fio": "Duplicate", "group_id": chain["group"], "student_no": "TEST-001"},
        ),
        ("/api/disciplines", {"name": "DevOps"}),
        (
            "/api/plans",
            {"group_id": chain["group"], "discipline_id": chain["discipline"], "semester": 5},
        ),
    ]
    client.post("/api/login", json={"username": "admin", "password": os.environ["ADMIN_PASSWORD"]})
    for url, payload in requests:
        assert client.post(url, json=payload).status_code == 400
        assert client.get("/api/me").status_code == 200
    assert client.post("/api/grades", json=grade(chain)).status_code == 201
    assert client.post("/api/grades", json=grade(chain)).status_code == 400
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/groups", json={"name": "AFTER-ERROR", "year": 2026}).status_code == 201


@pytest.mark.parametrize(
    "url,payload",
    [
        ("/api/groups", {"name": "x", "year": "bad"}),
        ("/api/students", {"fio": "x", "group_id": "bad", "student_no": "X"}),
        ("/api/students", {"fio": "x", "group_id": 999999, "student_no": "X"}),
        ("/api/disciplines", {"name": "x", "credits": "bad"}),
        ("/api/plans", {"group_id": 999999, "discipline_id": 999999, "semester": 5}),
    ],
)
def test_invalid_references_and_numbers(client, url, payload):
    assert client.post(url, json=payload).status_code == 400


def test_authentication(client, db):
    password = secrets.token_urlsafe(20)
    data = {"username": "teacher_test", "password": password}
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/register", json=data).status_code == 201
    assert client.get("/api/me").get_json()["username"] == data["username"]
    stored = db.execute(
        "SELECT password_hash FROM users WHERE username=%s", (data["username"],)
    ).fetchone()[0]
    assert stored != password and password not in stored
    assert client.post("/api/register", json=data).status_code == 400
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/login", json={**data, "password": "incorrect"}).status_code == 401
    assert client.post("/api/login", json=data).status_code == 200
    assert client.get("/api/me").status_code == 200


@pytest.mark.parametrize(
    "payload", [{"username": 5, "password": []}, {"username": "t", "password": "x"}]
)
def test_bad_auth_inputs(client, payload):
    assert client.post("/api/register", json=payload).status_code == 400
    assert client.post("/api/login", json=payload).status_code == 401


def test_average_numeric_and_null_last(client, chain, db):
    client.post("/api/grades", json=grade(chain))
    did = db.execute("INSERT INTO disciplines(name) VALUES ('SECOND') RETURNING id").fetchone()[0]
    db.execute(
        "INSERT INTO study_plans(group_id,discipline_id,semester) VALUES (%s,%s,5)",
        (chain["group"], did),
    )
    db.execute(
        "INSERT INTO grades(student_id,discipline_id,semester,value) VALUES (%s,%s,5,4)",
        (chain["student"], did),
    )
    db.execute(
        "INSERT INTO students(fio,group_id,student_no) VALUES ('Без оценок',%s,'EMPTY')",
        (chain["group"],),
    )
    db.commit()
    rows = client.get("/api/report/avg").get_json()
    assert rows[0]["avg_score"] == 4.5 and isinstance(rows[0]["avg_score"], float)
    assert rows[0]["cnt"] == 2
    assert rows[-1]["avg_score"] is None and rows[-1]["cnt"] == 0


def test_database_comment_constraint(chain, db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "INSERT INTO grades(student_id,discipline_id,semester,value,comment) VALUES (%s,%s,5,5,%s)",
            (chain["student"], chain["discipline"], "я" * 501),
        )
    db.rollback()


def test_admin_idempotent(app_module, db):
    before = db.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()[0]
    with app_module.app.app_context():
        app_module.init_db()
    after = db.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()[0]
    assert before == after


def test_health_failure_redacts_password(client, app_module, monkeypatch, caplog):
    password = app_module.DB_CONFIG["password"]

    def fail():
        raise psycopg.OperationalError(f"DB unavailable {password}")

    monkeypatch.setattr(app_module, "get_db", fail)
    response = client.get("/health")
    assert response.status_code == 500
    assert response.get_json() == {"status": "fail"}
    assert password not in caplog.text and "[redacted]" in caplog.text
    assert client.get("/version").status_code == 200
