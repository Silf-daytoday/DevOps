#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ERRORS=0
CHECKS=0

check_file() {
    local description="$1"
    local file="$2"
    local pattern="$3"

    CHECKS=$((CHECKS + 1))

    if [[ -f "$file" ]] && grep -Eq -- "$pattern" "$file"; then
        echo "[OK] $description"
    else
        echo "[FAIL] $description"
        ERRORS=$((ERRORS + 1))
    fi
}

echo "===== CONTAINER CHECK ====="

# Наличие файлов
for file in Dockerfile compose.app.yaml compose.db.yaml .dockerignore; do
    CHECKS=$((CHECKS + 1))
    if [[ -f "$file" ]]; then
        echo "[OK] $file exists"
    else
        echo "[FAIL] $file missing"
        ERRORS=$((ERRORS + 1))
    fi
done

# Dockerfile
check_file "Non-root APP user 10001" Dockerfile '^USER 10001:10001$'
check_file "Dockerfile HEALTHCHECK" Dockerfile '^HEALTHCHECK'
check_file "Gunicorn startup" Dockerfile 'gunicorn'

# APP security and limits
check_file "APP read-only filesystem" compose.app.yaml 'read_only:[[:space:]]*true'
check_file "APP no-new-privileges" compose.app.yaml 'no-new-privileges:true'
check_file "APP drops all capabilities" compose.app.yaml 'cap_drop:'
check_file "APP memory limit 1g" compose.app.yaml 'mem_limit:[[:space:]]*1g'
check_file "APP CPU limit 1.0" compose.app.yaml 'cpus:[[:space:]]*1\.0'
check_file "APP PID limit 100" compose.app.yaml 'pids_limit:[[:space:]]*100'
check_file "APP temporary filesystem" compose.app.yaml 'tmpfs:'
check_file "APP Docker secrets" compose.app.yaml 'secrets:'
check_file "APP DB password secret" compose.app.yaml 'db_password'
check_file "APP secret key" compose.app.yaml 'secret_key'
check_file "APP admin password secret" compose.app.yaml 'admin_password'

# DB security and persistence
check_file "DB persistent PostgreSQL volume" compose.db.yaml 'postgres_data:/var/lib/postgresql/data'
check_file "DB memory limit 1536m" compose.db.yaml 'mem_limit:[[:space:]]*1536m'
check_file "DB CPU limit 1.0" compose.db.yaml 'cpus:[[:space:]]*1\.0'
check_file "DB PID limit 100" compose.db.yaml 'pids_limit:[[:space:]]*100'
check_file "DB healthcheck" compose.db.yaml 'healthcheck:'
check_file "DB Docker secrets" compose.db.yaml 'secrets:'
check_file "DB no-new-privileges" compose.db.yaml 'no-new-privileges:true'

# Secrets must not enter Git or Docker build context
check_file "Secrets excluded from Git" .gitignore '^secrets/$'
check_file "Secrets excluded from Docker context" .dockerignore '^secrets/$'

# Dangerous configuration
for file in compose.app.yaml compose.db.yaml; do
    CHECKS=$((CHECKS + 1))
    if grep -Eq '^[[:space:]]*privileged:[[:space:]]*true' "$file"; then
        echo "[FAIL] Privileged mode forbidden: $file"
        ERRORS=$((ERRORS + 1))
    else
        echo "[OK] No privileged mode: $file"
    fi
done

# Compose syntax validation, when Docker is available
if command -v docker >/dev/null 2>&1; then
    for file in compose.db.yaml compose.app.yaml; do
        if docker compose -f "$file" config --quiet; then
            echo "[OK] Compose syntax: $file"
            CHECKS=$((CHECKS + 1))
        else
            echo "[FAIL] Compose syntax: $file"
            ERRORS=$((ERRORS + 1))
        fi
    done
else
    echo "[SKIP] Docker CLI unavailable: Compose validation skipped"
fi

echo "=========================="
echo "Checks: $CHECKS"
echo "Errors: $ERRORS"

if (( ERRORS > 0 )); then
    echo "CONTAINER CHECK FAILED"
    exit 1
fi

echo "CONTAINER CHECK PASSED"
