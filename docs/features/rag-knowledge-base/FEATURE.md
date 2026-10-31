# RAG knowledge base

Contract: [docs/CONTRACTS.md](../../CONTRACTS.md) v1.0.0, section "RAG module interface". This folder must not redefine it.

**What:** a searchable knowledge base for the support agent's `search_kb` tool, built from curated product docs.
**Why:** the agent answers "how to" questions and recognises known errors with a cited `kb_id`; case-specific evidence comes from logs, not from RAG.
**Owner:** Andrii.

## Scope (MVP)
- Ingest curated `data/docs/*.md` into `kb_global` (approved), one record per `## ` section.
- Extract customer tickets with Gemma into `kb_tenant` of their own tenant, always `pending_review` (never retrieved; automatic publication is disabled).
- `retrieve(query, context, intent=None, k=4) -> [{kb_id, text, score}]` over approved global + authenticated-tenant records.
- Security: PII redaction, injection rejection, intent/tool allowlists, tenant pre-filter, no customer content in `kb_global`.

## Acceptance criteria
- "Як створити промокод" returns a `promo_how_to` record in the top 2.
- "Промокод не проходить на касі" returns a `promo_not_applied` record in the top 2.
- "Двічі списали за підписку" returns a `double_charge` record in the top 2.
- `k` outside 1..10, unknown intent or empty tenant raise `ValueError`.
- A `kb_tenant` record of tenant_b is never returned for tenant_a. `pending_review` records are never returned.
- `kb_global` has no `tenant_id` and no ticket-derived records. No phone/email/card number is stored.

Out of scope: review UI for `pending_review`, judge-based publication, tone analysis, Atlas cloud deploy.
