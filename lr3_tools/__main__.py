"""CLI обслуживания: python -m lr3_tools --help."""

import argparse
import sys

from lr3_tools.backup import backup, restore
from lr3_tools.checks import check_backup, check_migrations
from lr3_tools.common import Database, redact
from lr3_tools.migrate import baseline, upgrade


def main():
    parser = argparse.ArgumentParser(description="ЛР3: управляемое обслуживание PostgreSQL")
    parser.add_argument(
        "action",
        choices=("migrate", "baseline", "backup", "restore", "migration-check", "backup-check"),
    )
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--database")
    parser.add_argument("--file")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    try:
        if args.action in ("migration-check", "backup-check"):
            if args.production or args.database:
                raise ValueError("Проверки используют только фиксированные тестовые базы")
            (check_migrations if args.action == "migration-check" else check_backup)()
            return 0
        spec = Database.from_env(args.database, args.production)
        if args.action == "migrate":
            upgrade(spec)
        elif args.action == "baseline":
            baseline(spec)
        elif args.action == "backup":
            if not args.file:
                raise ValueError("Укажите FILE=путь; существующий файл не перезаписывается")
            backup(spec, args.file)
        elif args.action == "restore":
            if not args.file:
                raise ValueError("Укажите FILE=путь и CONFIRM_RESTORE=имя_БД")
            restore(spec, args.file, args.confirm)
        return 0
    except Exception as exc:
        print(redact(f"ОШИБКА: {exc}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
