# Data model (db `support`)

Fields follow docs/CONTRACTS.md "MongoDB contracts"; this file only notes RAG specifics.

## kb_global
`kb_id` (`KB-<INTENT>-NNN`), `title`, `text`, `embedding[768]`, `embedding_model`, `intent`, `status` (approved), `created_at`, `updated_at`. No `tenant_id`, no customer content.
Vector index `kb_vector`: cosine on `embedding`; filters `status`, `intent`.

## kb_tenant
Same fields plus `tenant_id`; `kb_id` = `KBT-<tenant>-<INTENT>-NNN`; ticket-derived records are `pending_review`.
Vector index `kb_vector`: filters `tenant_id`, `status`, `intent`.

## ingest_log (RAG-internal audit, not in the contract)
`tenant_id?`, `source_id`, `kb_id?`, `collection?`, `action` (inserted|merged|rejected), `status?`, `reason?`, `at`.
