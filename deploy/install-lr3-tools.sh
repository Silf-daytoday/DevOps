#!/usr/bin/env bash
# Инструменты администратора на db-server, отдельно от runtime приложения.
set -euo pipefail
umask 022
if [[ "$EUID" -ne 0 ]]; then
    echo 'Запустите через sudo bash deploy/install-lr3-tools.sh' >&2
    exit 1
fi
source_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
target=/opt/devops/lr3-tools
install -d -o root -g root -m 0755 "$target"
for file in Makefile requirements.txt requirements-dev.txt alembic.ini; do
    install -o root -g root -m 0644 "$source_dir/$file" "$target/$file"
done
for directory in lr3_tools migrations; do
    while IFS= read -r -d '' file; do
        relative=$file
        relative=$(realpath --relative-to="$source_dir" "$file")
        install -D -o root -g root -m 0644 "$file" "$target/$relative"
    done < <(find "$source_dir/$directory" -type f ! -path '*/__pycache__/*' -print0)
done
python3 -m venv "$target/.venv"
"$target/.venv/bin/python" -m pip install -r "$target/requirements-dev.txt"
"$target/.venv/bin/python" -m pip check
install -d -o postgres -g postgres -m 0700 /var/backups/devops
echo 'Готово: /opt/devops/lr3-tools. Миграции и восстановление не запускались.'
