#!/usr/bin/env bash
set -Eeuo pipefail

APP_PASSWORD="$(cat /run/secrets/db_password)"

psql --username "$POSTGRES_USER" \
     --dbname devops \
     --set=ON_ERROR_STOP=1 \
     --set=app_password="$APP_PASSWORD" <<'SQL'
ALTER ROLE devops_app WITH PASSWORD :'app_password';
SQL

unset APP_PASSWORD
