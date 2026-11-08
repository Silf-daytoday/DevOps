"""Проверка целевой БД до операций обслуживания."""

import os
from dataclasses import dataclass
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASES = (
    "devops_test",
    "devops_lr3_clean",
    "devops_lr3_upgrade",
    "devops_lr3_restore",
)
BUSINESS_TABLES = ("groups", "students", "disciplines", "study_plans", "grades", "users")


@dataclass(frozen=True)
class Database:
    host: str
    port: int
    name: str
    user: str
    password: str
    production: bool = False

    def __post_init__(self):
        if self.production:
            if self.name != "devops" or self.user != "postgres" or not self.host.startswith("/"):
                raise ValueError(
                    "Основная БД доступна инструментам только через локального postgres"
                )
        elif self.name not in TEST_DATABASES or self.user != "devops_test":
            raise ValueError("ОТКАЗ: запрещены нетестовая БД или пользователь")
        if not self.host or self.host.startswith("CHANGE_ME"):
            raise ValueError("Задайте DB_HOST")
        if not 1 <= self.port <= 65535:
            raise ValueError("Некорректный DB_PORT")
        if not self.production and (not self.password or self.password.startswith("CHANGE_ME")):
            raise ValueError("Задайте тестовый DB_PASSWORD")

    @classmethod
    def from_env(cls, name=None, production=False):
        return cls(
            host=os.environ.get("DB_HOST", ""),
            port=int(os.environ.get("DB_PORT", "5432")),
            name=name if name is not None else os.environ.get("DB_NAME", ""),
            user=os.environ.get("DB_USER", ""),
            password=os.environ.get("DB_PASSWORD", ""),
            production=production,
        )

    def kwargs(self):
        return dict(
            host=self.host,
            port=self.port,
            dbname=self.name,
            user=self.user,
            password=self.password or None,
            connect_timeout=5,
        )

    def check_identity(self, conn):
        actual = conn.execute("SELECT current_database(), current_user, session_user").fetchone()
        if tuple(actual) != (self.name, self.user, self.user):
            raise ValueError(
                "ОТКАЗ: фактические база или пользователь не соответствуют конфигурации"
            )

    def connect(self, owner=False):
        conn = psycopg.connect(**self.kwargs())
        try:
            self.check_identity(conn)
            if owner and self.production:
                conn.execute("SET ROLE devops_owner")
            return conn
        except Exception:
            conn.close()
            raise


def clear_test_database(spec):
    if spec.production:
        raise ValueError("ОТКАЗ: очистка основной БД запрещена")
    with spec.connect() as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public AUTHORIZATION devops_test")
        conn.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")


def redact(message):
    secret = os.environ.get("DB_PASSWORD", "")
    return message.replace(secret, "[redacted]") if secret else message
