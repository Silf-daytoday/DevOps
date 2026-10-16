#!/usr/bin/env bash
# Подготовка app-server. Запускается вручную: sudo bash deploy/install-app.sh
set -euo pipefail
umask 022

if [[ "$EUID" -ne 0 ]]; then
    echo 'Запустите через sudo bash deploy/install-app.sh' >&2
    exit 1
fi

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
for file in app.py requirements.txt .env.example deploy/devops-app.service; do
    [[ -f "$source_dir/$file" ]] || { echo "Нет файла $file" >&2; exit 1; }
done
command -v python3 >/dev/null
command -v systemctl >/dev/null

if ! id devopsapp >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home --shell /usr/sbin/nologin devopsapp
fi
if [[ "$(id -u devopsapp)" -eq 0 ]] || [[ " $(id -nG devopsapp) " == *' sudo '* ]]; then
    echo 'devopsapp должен быть непривилегированным отдельным пользователем' >&2
    exit 1
fi

install -d -o root -g root -m 0755 /opt/devops /opt/devops/app
install -o root -g root -m 0644 "$source_dir/app.py" /opt/devops/app/app.py
install -o root -g root -m 0644 "$source_dir/requirements.txt" /opt/devops/app/requirements.txt
python3 -m venv /opt/devops/venv
/opt/devops/venv/bin/python -m pip install -r /opt/devops/app/requirements.txt

install -d -o root -g root -m 0750 /etc/devops
if [[ ! -e /etc/devops/app.env ]]; then
    install -o root -g root -m 0600 "$source_dir/.env.example" /etc/devops/app.env
    echo 'Создан /etc/devops/app.env с заглушками; заполните его вручную.'
else
    echo 'Существующий /etc/devops/app.env сохранён.'
fi

install -o root -g root -m 0644 "$source_dir/deploy/devops-app.service" /etc/systemd/system/devops-app.service
systemd-analyze verify /etc/systemd/system/devops-app.service
systemctl daemon-reload
systemctl enable systemd-networkd-wait-online.service
echo 'Подготовка закончена. После схемы/прав БД и заполнения env: sudo systemctl enable --now devops-app'
