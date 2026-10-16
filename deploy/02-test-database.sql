-- Только отдельная devops_test. Повторное выполнение не очищает данные.
\set ON_ERROR_STOP on
SELECT 'CREATE ROLE devops_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'devops_test')
\gexec
SELECT 'CREATE DATABASE devops_test OWNER devops_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'devops_test')
\gexec
\connect devops_test
BEGIN;
REVOKE ALL ON DATABASE devops_test FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO devops_test;
SET ROLE devops_test;
\ir ../schema.sql
RESET ROLE;
COMMIT;
-- Пароль задаётся отдельно интерактивно: \password devops_test
