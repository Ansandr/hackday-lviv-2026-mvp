# Data model (db `support`)

## kb
`kb_id`, `type` (doc|policy|known_issue), `title`, `product_area` (promo|billing|venues|pos|staff|reports|other),
`symptom`, `cause`, `resolution_steps[]`, `action_tool` (allowlist or null), `body` (docs only),
`tenant_scope` (global|<tenant_id>), `source_ids[]`, `occurrences`, `status` (approved|pending_review),
`text` (embedded text), `embedding[768]`, `updated_at`.

Vector index `kb_vector`: cosine on `embedding`; filters `status`, `tenant_scope`, `product_area`, `type`.

## ingest_log
`source_id`, `kb_id?`, `action` (inserted|merged|rejected), `status?`, `reason?`, `at`.

## tickets
Contract shape from docs/CONTRACTS.md (filled by agent/ui).
