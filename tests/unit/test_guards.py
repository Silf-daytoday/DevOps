import pytest

from lr3_tools.common import Database


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_NAME", "devops_test")
    monkeypatch.setenv("DB_USER", "devops_test")
    monkeypatch.setenv("DB_PASSWORD", "test-only-placeholder")


def test_allowed_test_identity(env):
    assert Database.from_env().name == "devops_test"


@pytest.mark.parametrize("name", ["devops", "postgres", "anything", ""])
def test_main_database_refused_before_connection(env, monkeypatch, name):
    monkeypatch.setenv("DB_NAME", name)
    with pytest.raises(ValueError, match="ОТКАЗ"):
        Database.from_env()


def test_runtime_role_refused(env, monkeypatch):
    monkeypatch.setenv("DB_USER", "devops_app")
    with pytest.raises(ValueError, match="ОТКАЗ"):
        Database.from_env()


def test_production_requires_local_admin(env, monkeypatch):
    monkeypatch.setenv("DB_NAME", "devops")
    with pytest.raises(ValueError, match="Основная БД"):
        Database.from_env(production=True)


def test_wrong_actual_identity(env):
    class Cursor:
        def fetchone(self):
            return ("devops", "devops_app", "devops_app")

    class Connection:
        def execute(self, query):
            return Cursor()

    with pytest.raises(ValueError, match="фактические"):
        Database.from_env().check_identity(Connection())
