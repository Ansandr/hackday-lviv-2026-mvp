# End-to-end flow

## Ingestion (`python -m src.rag.ingest [--reset]`)
1. Ensure vector indexes `kb_vector` on `kb_global` (filters status, intent) and `kb_tenant` (filters tenant_id, status, intent) are queryable.
2. Each doc in `data/docs/`: read `<!-- intent: ... -->` (missing or unknown -> `other`), split by `## `, record text = section title + body, write to `kb_global`, status `approved`.
3. Each ticket in `data/tickets/`:
   1. If a customer message looks like prompt injection -> `ingest_log` `rejected`, stop.
   2. Redact PII, wrap the conversation in `<customer_message>`.
   3. Gemma (hosted Gemma 4 with local fallback, JSON) extracts title, intent, symptom, cause, steps, action_tool.
   4. `validate()` clamps intent and action_tool to allowlists; the fields are folded into `text`.
   5. Write to `kb_tenant` with the ticket's `tenant_id`, status `pending_review`.
4. Embed with `embeddinggemma`; if the nearest record in the same collection, tenant and intent has score >= 0.95 -> merge (touch `updated_at`), else insert.
5. Every step is written to `ingest_log`.

## Retrieval (`retrieve()`)
1. Validate k (1..10), intent (enum or None), `context.tenant_id` (non-empty).
2. Redact the query, embed it as a search query.
3. `$vectorSearch` on `kb_global` (status approved, intent?) and on `kb_tenant` (tenant_id = context, status approved, intent?).
4. Merge by score, return top-k `{kb_id, text, score}`.
