# End-to-end flow

## Ingestion (`python -m src.rag.ingest`)
1. Ensure the `kb_vector` index exists and is queryable.
2. Each doc in `data/docs/`: read the `<!-- area, type, tool -->` header, split by `## `, one record per section, status `approved`.
3. Each ticket in `data/tickets/`:
   1. If a customer message looks like prompt injection -> log `rejected`, stop.
   2. Redact PII, wrap the conversation in `<customer_message>`.
   3. Gemma (`gemma3:4b`, JSON mode) extracts title, area, symptom, cause, steps, action_tool.
   4. `validate()` clamps area and tool to allowlists.
   5. Status = `approved` if judge score >= 4 and policy_ok, else `pending_review`.
4. Embed with `embeddinggemma`; if the nearest record in the same area/type has score >= 0.95 -> merge (`occurrences++`), else insert.
5. Every step is written to `ingest_log`.

## Retrieval (`retrieve()`)
1. Redact the query, embed it as a search query.
2. `$vectorSearch` with pre-filter `status=approved`, `tenant_scope in [global, tenant_id]`, optional `product_area`.
3. Return top-k `kb_hit` (docs/CONTRACTS.md); the agent cites `kb_id`.
