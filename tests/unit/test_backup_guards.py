from contextlib import nullcontext

import pytest

from lr3_tools.backup import backup, restore
from lr3_tools.common import Database, clear_test_database


@pytest.fixture
def spec(monkeypatch):
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_NAME", "devops_test")
    monkeypatch.setenv("DB_USER", "devops_test")
    monkeypatch.setenv("DB_PASSWORD", "isolated-test-placeholder")
    return Database.from_env()


def test_backup_never_overwrites_existing_file(spec, tmp_path, monkeypatch):
    path = tmp_path / "original.dump"
    path.write_bytes(b"ORIGINAL")
    monkeypatch.setattr(Database, "connect", lambda self: nullcontext())
    with pytest.raises(FileExistsError):
        backup(spec, path)
    assert path.read_bytes() == b"ORIGINAL"


def test_failed_backup_is_removed(spec, tmp_path, monkeypatch):
    path = tmp_path / "failed.dump"
    monkeypatch.setattr(Database, "connect", lambda self: nullcontext())

    def fail(*args, **kwargs):
        kwargs["stdout"].write(b"PARTIAL")
        raise RuntimeError("simulated pg_dump failure")

    monkeypatch.setattr("lr3_tools.backup.run_pg", fail)
    with pytest.raises(RuntimeError):
        backup(spec, path)
    assert not path.exists()


def test_backup_permissions(spec, tmp_path, monkeypatch):
    path = tmp_path / "private.dump"
    monkeypatch.setattr(Database, "connect", lambda self: nullcontext())

    def dump(*args, **kwargs):
        kwargs["stdout"].write(b"PGDMP")

    monkeypatch.setattr("lr3_tools.backup.run_pg", dump)
    backup(spec, path)
    assert path.stat().st_mode & 0o777 == 0o600


def test_restore_requires_confirmation_before_connection(spec, tmp_path):
    with pytest.raises(ValueError, match="CONFIRM_RESTORE"):
        restore(spec, tmp_path / "missing.dump", "devops")


def test_restore_rejects_invalid_archive_before_connection(spec, tmp_path):
    path = tmp_path / "bad.dump"
    path.write_bytes(b"NOT A DUMP")
    with pytest.raises(ValueError, match="custom"):
        restore(spec, path, spec.name)


def test_cannot_construct_unsafe_database_directly():
    with pytest.raises(ValueError, match="ОТКАЗ"):
        Database("127.0.0.1", 5432, "devops", "postgres", "")


def test_cannot_clear_production():
    spec = Database("/var/run/postgresql", 5432, "devops", "postgres", "", production=True)
    with pytest.raises(ValueError, match="очистка"):
        clear_test_database(spec)
