"""Архивы PostgreSQL: аргументы без shell, пароль только через окружение."""

import os
import shutil

# Нужны штатные pg_dump/pg_restore; команды выполняются без shell.
import subprocess  # nosec B404
from pathlib import Path

from lr3_tools.migrate import grant_runtime


def pg_tool(name):
    if name not in ("pg_dump", "pg_restore"):
        raise ValueError("Неизвестный инструмент PostgreSQL")
    executable = shutil.which(name)
    if not executable:
        raise ValueError(f"Установите postgresql-client-16: не найден {name}")
    return str(Path(executable).absolute())


def run_pg(spec, name, extra, stdout=None):
    env = os.environ.copy()
    if spec.password:
        env["PGPASSWORD"] = spec.password
    else:
        env.pop("PGPASSWORD", None)
    args = [
        pg_tool(name),
        "--host",
        spec.host,
        "--port",
        str(spec.port),
        "--username",
        spec.user,
        "--no-password",
        *extra,
    ]
    # Абсолютный бинарник из закрытого списка, список argv, shell=False,
    # проверенные БД/пользователь, пароль отсутствует в argv; см. docs/LR3.md.
    subprocess.run(args, check=True, env=env, stdout=stdout)  # nosec B603


def backup(spec, filename):
    with spec.connect():
        pass
    path = Path(filename).expanduser().resolve()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # O_EXCL защищает исходную копию от перезаписи; 0600 независимо от umask.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            run_pg(spec, "pg_dump", ["--format=custom", "--dbname", spec.name], stdout=output)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    print(f"Резервная копия создана: {path}")
    return path


def restore(spec, filename, confirm):
    if confirm != spec.name:
        raise ValueError("ОТКАЗ: CONFIRM_RESTORE должен точно совпадать с целевой БД")
    path = Path(filename).expanduser().resolve(strict=True)
    with path.open("rb") as stream:
        if stream.read(5) != b"PGDMP":
            raise ValueError("Ожидается custom-архив pg_dump (-Fc)")
    with spec.connect():
        pass
    args = [
        "--clean",
        "--if-exists",
        "--exit-on-error",
        "--single-transaction",
        "--no-owner",
        "--no-acl",
        "--dbname",
        spec.name,
    ]
    if spec.production:
        args += ["--role", "devops_owner"]
    run_pg(spec, "pg_restore", [*args, str(path)])
    grant_runtime(spec)
    print(f"Восстановление {spec.name}: OK")
