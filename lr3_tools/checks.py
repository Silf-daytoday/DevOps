"""Проверки миграций и восстановления только на выделенных тестовых БД."""

import tempfile
from pathlib import Path

from alembic import command

from lr3_tools.backup import backup, restore
from lr3_tools.common import Database, clear_test_database
from lr3_tools.migrate import baseline, configuration, upgrade


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def seed(spec):
    with spec.connect() as conn:
        gid = conn.execute(
            "INSERT INTO groups(name,year) VALUES (%s,2026) RETURNING id", ("LR3-CONTROL",)
        ).fetchone()[0]
        sid = conn.execute(
            "INSERT INTO students(fio,group_id,student_no) VALUES (%s,%s,%s) RETURNING id",
            ("Контрольный студент", gid, "LR3-CONTROL-001"),
        ).fetchone()[0]
        did = conn.execute(
            "INSERT INTO disciplines(name) VALUES (%s) RETURNING id", ("ЛР3-контроль",)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO study_plans(group_id,discipline_id,semester) VALUES (%s,%s,5)",
            (gid, did),
        )
        conn.execute(
            "INSERT INTO grades(student_id,discipline_id,semester,value) VALUES (%s,%s,5,5)",
            (sid, did),
        )


def check_migrations():
    clean = Database.from_env("devops_lr3_clean")
    filled = Database.from_env("devops_lr3_upgrade")
    clear_test_database(clean)
    upgrade(clean)
    with clean.connect() as conn:
        revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        require(revision == "004_grade_created_at", "Неверная ревизия чистой БД")
        require(
            conn.execute("SELECT COUNT(*) FROM grades").fetchone()[0] == 0,
            "Проверка контрольных данных не пройдена",
        )
    print("MIGRATION CLEAN: OK")

    clear_test_database(filled)
    upgrade(filled, "001_lr2")
    # Имитируем реальную ЛР2 без alembic_version.
    with filled.connect() as conn:
        conn.execute("DROP TABLE alembic_version")
    seed(filled)
    with filled.connect() as conn:
        before = conn.execute("SELECT * FROM grades ORDER BY id").fetchall()
    baseline(filled)
    upgrade(filled)
    with filled.connect() as conn:
        after = conn.execute(
            "SELECT id,student_id,discipline_id,semester,value FROM grades ORDER BY id"
        ).fetchall()
        require(before == after, "Данные изменились при миграции")
        require(
            conn.execute("SELECT comment,created_at FROM grades").fetchone() == (None, None),
            "Проверка контрольных данных не пройдена",
        )
    # Проверяем обратимость только тестовой схемы, не основной БД.
    command.downgrade(configuration(filled), "001_lr2")
    upgrade(filled)
    print("MIGRATION POPULATED + BASELINE + DOWNGRADE/UPGRADE: OK")


def check_backup():
    spec = Database.from_env("devops_lr3_restore")
    clear_test_database(spec)
    upgrade(spec)
    seed(spec)
    with spec.connect() as conn:
        conn.execute("UPDATE grades SET comment=%s", ("Комментарий из копии",))
        before = snapshot(conn)
    with tempfile.TemporaryDirectory(prefix="lr3-backup-") as folder:
        filename = backup(spec, Path(folder) / "control.dump")
        with spec.connect() as conn:
            conn.execute("UPDATE groups SET name=%s", ("LR3-DAMAGED",))
            conn.execute("UPDATE grades SET value=2, comment=%s", ("Повреждено",))
            require(snapshot(conn) != before, "Повреждение не произошло")
        restore(spec, filename, spec.name)
        with spec.connect() as conn:
            require(snapshot(conn) == before, "Восстановленные данные отличаются")
            # Значение identity/sequence также должно восстановиться.
            next_id = conn.execute(
                "INSERT INTO groups(name,year) VALUES (%s,2026) RETURNING id", ("LR3-AFTER",)
            ).fetchone()[0]
            require(next_id > before["groups"][0][0], "Не восстановлена последовательность")
    print("BACKUP + DAMAGE + RESTORE + DATA/SEQUENCE CHECK: OK")


def snapshot(conn):
    # SQL содержит только имена из фиксированного списка.
    from psycopg import sql

    from lr3_tools.common import BUSINESS_TABLES

    return {
        table: conn.execute(
            sql.SQL("SELECT * FROM {} ORDER BY id").format(sql.Identifier("public", table))
        ).fetchall()
        for table in BUSINESS_TABLES
    }
