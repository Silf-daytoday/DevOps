-- sudo -u postgres psql -v ON_ERROR_STOP=1 -f этот_файл
-- Только выделенные тестовые базы. Существующие данные devops не затрагиваются.
\set ON_ERROR_STOP on
SELECT 'CREATE ROLE devops_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='devops_test')
\gexec
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='devops_test'
               AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication
                    OR rolbypassrls OR NOT rolcanlogin)) THEN
        RAISE EXCEPTION 'Проверьте привилегии devops_test: LOGIN без административных прав';
    END IF;
END $$;
SELECT format('CREATE DATABASE %I OWNER devops_test', name)
FROM (VALUES ('devops_test'), ('devops_lr3_clean'), ('devops_lr3_upgrade'),
             ('devops_lr3_restore')) AS databases(name)
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname=databases.name)
\gexec
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba
        WHERE d.datname IN ('devops_test','devops_lr3_clean','devops_lr3_upgrade','devops_lr3_restore')
          AND r.rolname <> 'devops_test'
    ) THEN
        RAISE EXCEPTION 'ОТКАЗ: владельцем всех тестовых БД должен быть devops_test';
    END IF;
END $$;
REVOKE ALL ON DATABASE devops_test FROM PUBLIC;
REVOKE ALL ON DATABASE devops_lr3_clean FROM PUBLIC;
REVOKE ALL ON DATABASE devops_lr3_upgrade FROM PUBLIC;
REVOKE ALL ON DATABASE devops_lr3_restore FROM PUBLIC;
-- Если роль создавалась впервые: \password devops_test
-- Существующий пароль не меняется.
