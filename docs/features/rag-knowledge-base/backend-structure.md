# Backend structure (`src/rag/`)

- `llm.py` - Ollama: `embed_doc`, `embed_query` (embeddinggemma, 768 dims, task prefixes), `chat_json` (Gemma JSON mode + 1 retry).
- `sanitize.py` - `redact` (PII), `looks_like_injection` (keyword heuristic), `as_data` (delimits untrusted text).
- `db.py` - Mongo client, collections, `ensure_index`, `vector_search`.
- `ingest.py` - `ingest_doc`, `ingest_ticket`, `validate`, `upsert` (dedup/merge).
- `retrieve.py` - `retrieve()` for the agent + CLI.

Mongo: `mongodb/mongodb-atlas-local` in Docker (`support-mongo`, port 27017) or Atlas via `MONGODB_URI`.
