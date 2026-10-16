-- Только для повторения с нуля. В уже настроенном окружении ПРОПУСТИТЬ.
\set ON_ERROR_STOP on
SET password_encryption = 'scram-sha-256';
CREATE ROLE devops_owner NOLOGIN;
CREATE ROLE devops_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE DATABASE devops OWNER devops_owner;
REVOKE ALL ON DATABASE devops FROM PUBLIC;
GRANT CONNECT ON DATABASE devops TO devops_app;
\connect devops
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO devops_owner;
GRANT USAGE ON SCHEMA public TO devops_app;
-- Пароль задаётся отдельно интерактивно: \password devops_app
