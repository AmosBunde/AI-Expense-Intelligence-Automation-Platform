-- Initialize PostgreSQL with required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create indexes for text search
-- (Tables created by Alembic migrations, this just ensures extensions are ready)
