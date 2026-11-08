import pytest

from lr3_tools.common import Database, clear_test_database
from lr3_tools.migrate import baseline, upgrade

pytestmark = pytest.mark.integration


def test_baseline_rejects_schema_drift_without_data_loss():
    spec = Database.from_env("devops_lr3_upgrade")
    clear_test_database(spec)
    upgrade(spec, "001_lr2")
    with spec.connect() as conn:
        conn.execute("DROP TABLE alembic_version")
        conn.execute("ALTER TABLE groups ADD COLUMN unexpected TEXT")
        conn.execute("INSERT INTO groups(name,year) VALUES ('DO-NOT-LOSE',2026)")
    with pytest.raises(ValueError, match="схема отличается"):
        baseline(spec)
    with spec.connect() as conn:
        assert conn.execute("SELECT name FROM groups").fetchone()[0] == "DO-NOT-LOSE"
        assert conn.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0] is None


def test_upgrade_requires_baseline_for_existing_schema():
    spec = Database.from_env("devops_lr3_clean")
    clear_test_database(spec)
    upgrade(spec, "001_lr2")
    with spec.connect() as conn:
        conn.execute("DROP TABLE alembic_version")
    with pytest.raises(ValueError, match="сначала make baseline"):
        upgrade(spec)
    with spec.connect() as conn:
        names = [
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='grades'"
            )
        ]
        assert "comment" not in names and "created_at" not in names


def test_baseline_rejects_changed_default():
    spec = Database.from_env("devops_lr3_upgrade")
    clear_test_database(spec)
    upgrade(spec, "001_lr2")
    with spec.connect() as conn:
        conn.execute("DROP TABLE alembic_version")
        conn.execute("ALTER TABLE disciplines ALTER COLUMN credits SET DEFAULT 9")
    with pytest.raises(ValueError, match="схема отличается"):
        baseline(spec)
