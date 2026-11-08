"""Управляемые миграции и проверка исходной схемы перед baseline."""

import json

from alembic import command
from alembic.config import Config
from psycopg import sql

from lr3_tools.common import BUSINESS_TABLES, ROOT


def signature(conn):
    tables = conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    ).fetchall()
    result = {}
    for (table,) in tables:
        if table == "alembic_version":
            continue
        columns = conn.execute(
            """SELECT a.attname, format_type(a.atttypid,a.atttypmod),
                      a.attnotnull, a.attidentity, pg_get_expr(d.adbin,d.adrelid)
               FROM pg_attribute a JOIN pg_class t ON t.oid=a.attrelid
               JOIN pg_namespace n ON n.oid=t.relnamespace
               LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
               WHERE n.nspname='public' AND t.relname=%s
                 AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""",
            (table,),
        ).fetchall()
        constraints = conn.execute(
            """SELECT c.contype, pg_get_constraintdef(c.oid)
               FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
               JOIN pg_namespace n ON n.oid=t.relnamespace
               WHERE n.nspname='public' AND t.relname=%s
               ORDER BY c.contype, pg_get_constraintdef(c.oid)""",
            (table,),
        ).fetchall()
        result[table] = {"columns": columns, "constraints": constraints}
    return json.loads(json.dumps(result))


def configuration(spec, baseline=False):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["database"] = spec
    cfg.attributes["baseline_approved"] = baseline
    return cfg


def baseline(spec):
    expected = json.loads((ROOT / "migrations/lr2_signature.json").read_text(encoding="utf-8"))
    with spec.connect() as conn:
        if conn.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0]:
            raise ValueError("Baseline уже задан; используйте make migrate")
        if signature(conn) != expected:
            raise ValueError("ОТКАЗ: схема отличается от исходной ЛР2; baseline не выполнен")
        if spec.production:
            owners = conn.execute(
                "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
            if any(owner != "devops_owner" for _, owner in owners):
                raise ValueError("ОТКАЗ: таблицы основной БД должны принадлежать devops_owner")
    command.stamp(configuration(spec, baseline=True), "001_lr2")
    print("Baseline 001_lr2: схема проверена, данные сохранены")


def upgrade(spec, revision="head"):
    command.upgrade(configuration(spec), revision)
    if spec.production:
        grant_runtime(spec)
    print(f"Миграции {spec.name}: {revision} OK")


def grant_runtime(spec):
    if not spec.production:
        return
    with spec.connect(owner=True) as conn:
        conn.execute("GRANT USAGE ON SCHEMA public TO devops_app")
        for table in BUSINESS_TABLES:
            conn.execute(
                sql.SQL("GRANT SELECT, INSERT ON {} TO devops_app").format(
                    sql.Identifier("public", table)
                )
            )
        conn.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO devops_app")
