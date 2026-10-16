-- Применение к существующей базе devops. Запускать через sudo -u postgres psql.
\set ON_ERROR_STOP on
\connect devops
BEGIN;
SET ROLE devops_owner;
\ir ../schema.sql
RESET ROLE;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO devops_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO devops_app;
COMMIT;
