# Team synchronization checkpoint

This file records observed implementation state. Interface definitions live only in [CONTRACTS.md](CONTRACTS.md).
Update this checkpoint after meaningful synchronization, not after every unchanged fetch.

## 2026-10-31: shared context baseline

- Inspected remote: `origin/main` at `3439040`.
- Fetch succeeded. Local HEAD and origin/main matched before this documentation change.
- Present implementation: `src/hello_gemma.py`, `src/hello_local.py`, and `src/tools_demo.py` provider examples.
- No frontend, FastAPI service, tenant repositories, scenario tools, or integrated RAG implementation was present at that checkpoint.
- Current task: establish shared context and one canonical contract under explicit user instruction.
- Contract v1 supersedes the initial sketch. It is a target interface, not a claim of completed implementation.
- Team notification: pending. No external team message was sent by this agent.
- Owner acknowledgment: no longer required under the subsequent user authorization below.

## Prepared team notice

The MVP scope is now three scenarios: promo failure, duplicate subscription charge, and promo creation.
Read AGENTS.md first. docs/CONTRACTS.md is the canonical interface and database specification.
The previous Ticket/Analysis/Agent result/Judge sketch is superseded by the v1 contracts.
Conversation persistence belongs to the API. Automatic judge-based KB publication is outside the MVP.
Frontend, agent, backend, and RAG owners must review the migration notes before integration.
Further contract changes require a repository notice. The user authorizes direct integration without PR reviews or owner acknowledgments.

## Checkpoint format

For later entries, record the date, inspected remote commit, changed components, compatibility findings, checks, and unresolved coordination items.
Reference actual commits or PRs. Do not describe uncommitted teammate work as integrated.

## 2026-10-31: direct-main workflow and remote inspection

- User explicitly authorized push and merge to main without PR approval waits.
- Inspected origin/main at 3439040 and origin/feat/andrii-rag at 59bea05.
- The RAG branch contains ingestion, retrieval, seed data, and tests. It is not yet merged into main.
- Its retrieve function still accepts tenant_id/product_area and returns the initial kb_hit shape.
- Its storage uses tenant_scope in a shared KB, unlike the v1 target collections.
- These are known migration differences for later RAG integration. This documentation change does not merge or rewrite that feature branch.
- Publish this baseline notice with the main push. No external team message was sent.
- PR approvals and owner acknowledgments are not merge gates. Contract notices and compatibility checks remain required.

## 2026-10-31: refund-request scope addition

- Inspected origin/main at 0137b83. The checkout was current and clean before this update.
- User requested that the agent offer a refund request after a duplicate charge.
- Contract 1.1.0 adds create_refund_request and refund_requests within the existing double_charge scenario.
- Separate confirmation is required. The result is a pending review request, never an executed refund.
- API/DB: add validation, tenant isolation, persistence, audit, and uniqueness per target payment.
- Agent: offer the request with evidence independently of subscription cancellation.
- Frontend: support the new action variant and show request ID, amount, and pending review status.
- RAG: describe request submission separately from actual refund approval and execution.
- Update validators and renderers before enabling the new action. Existing three actions retain their behavior.
- This commit updates specifications and acceptance criteria only. Runtime implementation remains pending.

## 2026-10-31: RAG migrated to contract v1 and merged to main

- Inspected origin/main at 67c0e31 (contract 1.1.0) and merged it; TEAM-SYNC conflict resolved by keeping both entries.
- `src/rag/` implements `retrieve(query, context, intent=None, k=4) -> [{kb_id, text, score}]` per CONTRACTS.md (unchanged in 1.1.0).
  RequestContext dataclass lives in `src/rag/retrieve.py` until the API defines its own; any object with `tenant_id` works.
- Storage: `kb_global` (curated `data/docs`, approved, no tenant_id) and `kb_tenant` (ticket extractions, always `pending_review`), one `kb_vector` index each.
- Curated corpus rewritten for the three scenarios (`data/docs/*.md`, header `<!-- intent: ... -->`). Refund/venue-onboarding docs removed.
- Embeddings: local Ollama `embeddinggemma` (768). Ticket extraction: hosted Gemma 4 (`GEMMA_MODEL`) with fallback to local `gemma3:4b`.
- Checks: `python -m src.rag.ingest --reset` on local `mongodb-atlas-local`, then `pytest tests`: 17 passed (offline + live: three scenarios, intent filter, KbHit shape, pending never returned, tenant isolation, kb_global has no customer content).
- Not yet done: Atlas shared cluster (guide in docs/ATLAS-SETUP.md), `search_kb` tool wrapper in the agent (agent owner), event name for retried signup in data/docs/error-codes.md is `SUBSCRIPTION_CREATE_RETRY` and must match the mock's logs.

## 2026-10-31: module owners assigned

- `src/backend/` (mock SaaS, seed, 4 actions, FastAPI `/api/v1` app): Макс (denisk0m).
- `src/agent/` (Gemma tool loop, dispatcher, `search_kb` wrapper, AgentTurn) and `src/ui/`: Володя (Husiak-V).
- `src/rag/`, `data/`: Andrii.
- Seam: agent calls `src/backend` Python methods and `src.rag.retrieve()` in-process; UI talks only to `/api/v1` (docs/INTEGRATION-REQUIREMENTS.md).

## 2026-10-31 15:40: owners reassigned (supersedes the previous owner entry)

- Andrii: `src/rag` (done), `src/agent` (Gemma tool loop + `search_kb`, bridge `turn`) and `src/backend` (mock SaaS seed + bridge `prepare`/`execute` for the 4 actions).
- Макс (denisk0m): support API + UI (`src/support`, `src/ui`) on `feat/support-service`; merges it to main himself.
- Володя (Husiak-V): out of AI limits. Waiting for him to push all his changes; then the team takes over his work.
- Integration: in-process Python bridge passed to `create_app(bridge=...)`; no separate agent/SaaS HTTP services for the demo.
