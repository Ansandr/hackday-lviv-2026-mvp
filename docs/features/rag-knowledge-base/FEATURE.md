# RAG knowledge base

**What:** a searchable knowledge base for the support agent, built automatically from product docs and resolved tickets.
**Why:** the agent answers "how to" questions with a cited source and knows known issues + which tool fixes them, so fewer tickets reach people.
**Owner:** Andrii.

## Scope (MVP)
- Ingest `data/docs/*.md` (one record per section) and `data/tickets/*.json` (Gemma extracts a structured record).
- Dedup similar records (`occurrences` counter = signal for developers).
- `retrieve(query, tenant_id, product_area, k)` for the agent.
- Security: PII redaction, injection rejection, judge gate, tenant pre-filter, tool allowlist.

## Acceptance criteria
- "Як створити промокод" returns a `promo` doc record in the top 2.
- "Промокод не проходить на касі" returns records whose `action_tool` is `resync_pos` / `check_promo` / `extend_promo`.
- "Двічі списали за підписку" returns the refund policy (limit 2000 UAH) in the top 2.
- Tickets with injection text are rejected; tickets with judge score < 4 or policy violation are `pending_review` and never retrieved.
- No phone/email/card number is stored in `kb`.

Out of scope: UI for reviewing `pending_review`, Atlas cloud deploy, re-ingesting on doc edits.
