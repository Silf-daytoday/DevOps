"""Все интеграционные тесты ограничены фактической devops_test/devops_test."""

import importlib
import os
import secrets

import pytest

from lr3_tools.common import Database, clear_test_database
from lr3_tools.migrate import upgrade


@pytest.fixture(scope="session")
def app_module():
    spec = Database.from_env()
    if spec.name != "devops_test":
        raise ValueError("Интеграционные тесты требуют DB_NAME=devops_test")
    clear_test_database(spec)
    upgrade(spec)
    os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))
    os.environ.setdefault("ADMIN_PASSWORD", secrets.token_urlsafe(24))
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture
def db(app_module):
    with Database.from_env("devops_test").connect() as conn:
        conn.execute(
            "TRUNCATE grades, study_plans, students, disciplines, groups, users RESTART IDENTITY"
        )
        conn.commit()
        with app_module.app.app_context():
            app_module.init_db()
        yield conn
        conn.rollback()


@pytest.fixture
def client(app_module, db):
    return app_module.app.test_client()


@pytest.fixture
def logged(client):
    response = client.post(
        "/login", data={"username": "admin", "password": os.environ["ADMIN_PASSWORD"]}
    )
    assert response.status_code == 302
    return client


@pytest.fixture
def chain(db):
    group = db.execute(
        "INSERT INTO groups(name,year) VALUES ('TEST-GROUP',2026) RETURNING id"
    ).fetchone()[0]
    student = db.execute(
        "INSERT INTO students(fio,group_id,student_no) VALUES ('Студент',%s,'TEST-001') RETURNING id",
        (group,),
    ).fetchone()[0]
    discipline = db.execute(
        "INSERT INTO disciplines(name,credits) VALUES ('DevOps',3) RETURNING id"
    ).fetchone()[0]
    db.execute(
        "INSERT INTO study_plans(group_id,discipline_id,semester) VALUES (%s,%s,5)",
        (group, discipline),
    )
    db.commit()
    return {"group": group, "student": student, "discipline": discipline}
