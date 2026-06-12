-- Create vector extension for pgvector support
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- RAGs table
CREATE TABLE IF NOT EXISTS rags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT, 
    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    public BOOLEAN NOT NULL DEFAULT FALSE,
    -- relations
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    original_file_name VARCHAR(255) NOT NULL,
    stored_key UUID UNIQUE NOT NULL, -- files are saved as `{storage_key}.pdf`
    file_length INTEGER NOT NULL,
    status VARCHAR(255) NOT NULL
    CHECK (status IN (
        'pending',
        'processing',
        'uploaded',
        'error'
    )),
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- relations
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rag_id INTEGER NOT NULL REFERENCES rags(id) ON DELETE CASCADE
);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    page_number INTEGER NOT NULL,
    content TEXT NOT NULL, -- sample, not the entire chunk
    embedding VECTOR(768),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- relations
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    rag_id INTEGER NOT NULL REFERENCES rags(id) ON DELETE CASCADE
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    temperature REAL NOT NULL,
    query TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
    CHECK (status IN (
        'pending',
        'processing',
        'completed',
        'error'
    )),
    response TEXT NOT NULL DEFAULT '[n/a]',
    -- relations
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rag_id INTEGER NOT NULL REFERENCES rags(id) ON DELETE CASCADE
);

-- Citations table
CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- relations
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE
);


-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_rags_owner_id ON rags(user_id);

CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_belongs_to ON documents(rag_id);

CREATE INDEX IF NOT EXISTS idx_chunks_found_in ON chunks(rag_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedded_in ON chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_jobs_queried_by ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_rag ON jobs(rag_id);