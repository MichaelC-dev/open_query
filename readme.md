# `open_query` - a Multi-Tenant API for hosting RAGs.

`open_query` is a FastAPI-based RAG service that lets users register, create RAG collections, upload PDF documents, and run queries against embedded document chunks stored in PostgreSQL with pgvector.

## Prerequisites

- Docker and Docker Compose


## Setup

1. Create the environment file:

	```bash
	cp .env-example .env
	```

	Update values as needed (Postgres credentials, DOC_LOCATION, etc.).


2. Start the full stack (API + PostgreSQL + pgvector + Ollama):

	```bash
	docker compose up --build
	```

	This will:
	- Start the FastAPI app on http://localhost:8000
	- Start PostgreSQL with pgvector enabled
	- Start the Ollama service for embeddings and chat models
	- Initialise the database schema from init/

3. Pull the required ollama models:

	```bash
	docker compose exec ollama ollama pull nomic-embed-text
	docker compose exec ollama ollama pull qwen2.5:1.5b
	```

4. Verify that the API is running, by contacting `GET http://localhost:8000/`.


## Important Endpoints

The API is organized around users, RAG collections, and background jobs.

### Users

- `POST /user/` - create a new account
- `POST /user/login` - authenticate and receive a bearer token
- `GET /user/` - fetch the current user profile
- `PATCH /user/` - update username and/or password
- `DELETE /user/` - delete the current account

### RAG collections

- `POST /rags/` - create a new RAG collection
- `GET /rags/{id}` - read a RAGs metadata
- `GET /rags/` - read metadata about all public RAGs
- `PATCH /rags/{id}` - update collection name or visibility
- `DELETE /rags/{id}` - delete a collection
- `POST /rags/ingest/{id}` - upload PDF files for ingestion
- `POST /rags/query/{id}` - queue a question against the given RAG

### Jobs

- `GET /jobs/{id}` - inspect a queued or completed query job and its citations

The root endpoint `GET /` returns a simple health response.

## Architecture

The application is split into a few focused layers:

- `src/app.py` boots FastAPI, opens the database session dependency, mounts the routers, and starts the background worker thread on startup.
- `src/routers/` contains the HTTP API for users, RAG collections, and jobs.
- `src/worker/dispatch.py` owns the in-memory job queue and dispatches document ingestion and query jobs.
- `src/services/ingestor.py` reads uploaded PDFs, extracts text, chunks it, and stores embeddings in PostgreSQL.
- `src/services/llm_service.py` embeds the user query, finds the closest chunks with pgvector cosine distance, builds the prompt, and calls Ollama to generate the answer.
- `src/db.py` builds the SQLAlchemy engine from Postgres environment variables.
- `init/01-vector.sql` creates the schema and enables the pgvector extension.

Data flow is straightforward: a user uploads a PDF into a RAG collection, the worker embeds and stores the chunks, and later queries use vector similarity to gather the most relevant chunks before calling the LLM.

## Project Status

While `open_query` is operational, it is an actively evolving project. Future improvements may include migrating the current in-memory job processing system to a more robust solution (such as Celery). Further architectural refinements are also being reviewed to improve scalability, maintainability, and overall system performance. Finally additional security measures (such as more exhaustive authentication controls, rate limiting, and deployment best practices) should be implemented before production use.

## Notes

- a `.env` file is used for managing system variables. a `.env-example` file has been provided as a template for the required `.env` file.
- Database configuration comes from `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`.
- File uploads expect `DOC_LOCATION` to point to a writable directory.
- Query and ingestion behavior depends on the embedding model and chat model configured through the Ollama-related environment variables.