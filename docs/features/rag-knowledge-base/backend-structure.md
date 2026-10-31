# Backend structure (`src/rag/`)

- `llm.py` - `embed_doc`, `embed_query` (local embeddinggemma, 768 dims, task prefixes), `chat_json` (hosted Gemma 4 via Gemini API, retries, local Gemma fallback).
- `sanitize.py` - `redact` (PII), `looks_like_injection` (keyword heuristic), `as_data` (delimits untrusted text).
- `db.py` - Mongo client, `kb_global`, `kb_tenant`, `ingest_log`, `ensure_indexes`, `vector_search(coll, ...)`.
- `ingest.py` - `ingest_doc`, `ingest_ticket`, `validate`, `ticket_text`, `parse_header`, `upsert`.
- `retrieve.py` - `RequestContext`, `INTENTS`, `retrieve()` + CLI.

Mongo: `mongodb/mongodb-atlas-local` in Docker (`support-mongo`, port 27017) or Atlas via `MONGODB_URI`.
