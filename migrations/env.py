"""Запуск через проверяющую обёртку make migrate/make baseline."""

from alembic import context
from sqlalchemy import URL, create_engine, pool, text

spec = context.config.attributes.get("database")
if spec is None:
    raise RuntimeError("Используйте make migrate или make baseline с проверкой целевой БД")

url = URL.create(
    "postgresql+psycopg",
    username=spec.user,
    password=spec.password or None,
    host=spec.host,
    port=spec.port,
    database=spec.name,
)
engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
with engine.begin() as connection:
    spec.check_identity(connection.connection.driver_connection)
    version_table = connection.execute(
        text("SELECT to_regclass('public.alembic_version')")
    ).scalar()
    populated = connection.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public')")
    ).scalar()
    if not version_table and populated and not context.config.attributes.get("baseline_approved"):
        raise ValueError("Существующая схема: сначала make baseline после резервного копирования")
    if spec.production:
        connection.execute(text("SET ROLE devops_owner"))
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
