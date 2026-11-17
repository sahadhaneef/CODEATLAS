-- Local development only. Never use these credentials outside loopback-only development.
CREATE ROLE codeatlas_app LOGIN PASSWORD 'local-app-only' NOSUPERUSER NOBYPASSRLS;
GRANT CONNECT ON DATABASE codeatlas TO codeatlas_app;
GRANT USAGE ON SCHEMA public TO codeatlas_app;
ALTER DEFAULT PRIVILEGES FOR ROLE codeatlas IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO codeatlas_app;
