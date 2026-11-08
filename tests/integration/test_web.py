import os
import secrets

import pytest

pytestmark = pytest.mark.integration


def test_index_and_auth_pages(client):
    assert "Успеваемость" in client.get("/").get_data(as_text=True)
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.post("/web/groups", data={"name": "X", "year": 2026}).status_code == 302
    assert client.post("/login", data={"username": "missing", "password": "bad"}).status_code == 401
    assert client.post("/register", data={"username": "x", "password": "x"}).status_code == 400


def test_web_auth_roundtrip(client):
    data = {"username": "web_teacher", "password": secrets.token_urlsafe(20)}
    assert client.post("/register", data=data).status_code == 302
    assert client.get("/login").status_code == 302
    assert client.get("/register").status_code == 302
    assert client.get("/logout").status_code == 302
    assert client.post("/register", data=data).status_code == 400
    assert client.post("/login", data=data).status_code == 302
    assert client.get("/").status_code == 200


def test_web_create_and_escape(logged, db):
    assert logged.post("/web/groups", data={"name": "WEB", "year": 2026}).status_code == 302
    gid = db.execute("SELECT id FROM groups WHERE name='WEB'").fetchone()[0]
    assert (
        logged.post(
            "/web/students", data={"fio": "WEB Student", "group_id": gid, "student_no": "WEB-1"}
        ).status_code
        == 302
    )
    sid = db.execute("SELECT id FROM students WHERE student_no='WEB-1'").fetchone()[0]
    assert logged.post("/web/disciplines", data={"name": "WEB Discipline"}).status_code == 302
    did = db.execute("SELECT id FROM disciplines WHERE name='WEB Discipline'").fetchone()[0]
    assert (
        logged.post(
            "/web/plans", data={"group_id": gid, "discipline_id": did, "semester": 5}
        ).status_code
        == 302
    )
    payload = {
        "student_id": sid,
        "discipline_id": did,
        "semester": 5,
        "value": 5,
        "comment": "<script>alert(1)</script>",
    }
    assert logged.post("/web/grades", data=payload).status_code == 302
    html = logged.get("/").get_data(as_text=True)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "Время записи" in html and "Комментарий" in html


def test_web_errors_and_rollback(logged, chain, db):
    assert logged.post("/web/groups", data={"name": "TEST-GROUP", "year": 2026}).status_code == 400
    assert logged.get("/").status_code == 200
    assert logged.post("/web/groups", data={"name": "BAD", "year": "abc"}).status_code == 400
    payload = {
        "student_id": chain["student"],
        "discipline_id": chain["discipline"],
        "semester": 5,
        "value": 5,
    }
    assert logged.post("/web/grades", data={**payload, "comment": "я" * 501}).status_code == 400
    assert logged.post("/web/grades", data={**payload, "value": 6}).status_code == 400
    db.execute("DELETE FROM study_plans")
    db.commit()
    assert logged.post("/web/grades", data=payload).status_code == 400


def test_cli_init_admin(app_module, db):
    result = app_module.app.test_cli_runner().invoke(args=["init-admin"])
    assert result.exit_code == 0
    assert "существующий пароль сохранён" in result.output
    assert os.environ["ADMIN_PASSWORD"] not in result.output
