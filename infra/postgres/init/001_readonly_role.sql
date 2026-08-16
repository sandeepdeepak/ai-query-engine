-- The application owner is used during early development and migrations.
-- Query execution will use this restricted login beginning in Phase 4.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ai_query_reader') THEN
    CREATE ROLE ai_query_reader LOGIN PASSWORD 'local_reader_only';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE ai_query_engine TO ai_query_reader;
GRANT USAGE ON SCHEMA public TO ai_query_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_query_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ai_query_reader;
ALTER ROLE ai_query_reader SET default_transaction_read_only = on;
ALTER ROLE ai_query_reader SET statement_timeout = '5s';

