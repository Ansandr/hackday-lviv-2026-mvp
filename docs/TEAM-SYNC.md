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

## 2026-10-31: independent support service branch

- Started feat/support-service from origin/main eb072de after fetching all remote branches.
- Main now includes the migrated RAG implementation and integration checklist. No SaaS or agent implementation was present in remote branches at inspection.
- User explicitly requests an independent support frontend and backend with executable agent proposals.
- Implemented src/support API, persistent conversations/session/action receipts, typed adapters and src/ui browser chat.
- Four action cards use immutable server-prepared previews; confirmation calls the SaaS adapter, never a browser-selected tool.
- Contract 1.2 records additional session/history routes and remote adapter boundaries. Existing action parameter shapes stay unchanged.
- Deliberate support-only shortcut: SQLite, single API worker; product and RAG remain MongoDB. SaaS must implement atomic idempotent execution.
- Demo mode is visibly labeled deterministic UI fixtures. It does not call AI or mutate the team's SaaS.
- Remote mode requires the agent turn and SaaS prepare/execute adapters. Their actual live integration remains pending.
- Launch and verification instructions: SUPPORT-SERVICE.md.

- Verification: 16 support API tests passed; full suite before the final three support checks: 22 passed, 1 live RAG module skipped (MongoDB unavailable). Browser checks passed with headless Edge: login, proposal, confirm, refund, responsive layout, no JavaScript errors.

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

- Synchronization: merged origin/main e9fa14e into feat/support-service. Kept both team checkpoint entries. Its owner assignment and single-process seam describe the parallel main plan; this branch implements the user-requested independent support service. Reconcile ownership with teammates before integrating duplicate UI/API work.

## 2026-10-31: pre-push teammate synchronization

- Fetched all remote refs before pushing. origin/main remains e9fa14e, origin/feat/andrii-rag remains eb072de, and origin/feat/support-service was 600c6a6.
- No new remote implementation commits. Main is already an ancestor of this branch; RAG changes are present.
- Confirmed unchanged existing four action argument shapes. Agent turn and SaaS preparation/execution adapters still require live implementation/integration.
- The ownership mismatch between main's recorded assignment and the user's independent-service request remains documented above; no teammate work was overwritten.
- Latest complete checks: 25 passed, 1 live RAG module skipped due to unavailable MongoDB; browser flow also passed.
- AGENTS.md now explicitly requires inspecting relevant teammate branches and interface compatibility before every push.

## 2026-10-31: Max takes agent and mock integration

- User explicitly states Volodya cannot continue. Max now completes agent, SaaS mock, support API and existing UI; Andrii continues RAG in parallel.
- Fetched main e9fa14e, andrii-rag eb072de, support-service e69ad0c before implementation. No new agent/mock code was published.
- Implemented src/agent JSON Gemma tool loop, strict read dispatcher, server-derived evidence and product-validated proposals.
- Implemented src/backend persisted two-tenant mock, correlated traces, four actions, version checks, atomic product/result/audit and refund deduplication.
- IntegratedBridge connects these components without an HTTP server per module. Existing remote adapters remain available.
- Product MongoDB uses one bounded tenant aggregate and atomic CAS; explicit SQLite fallback supports local integration. Local docs fallback is explicit, not vector search.
- Added one-command launcher. There is no configured GEMINI_API_KEY, MONGODB_URI or reachable Ollama on this machine; live AI/Atlas validation remains blocked by environment setup.
- No files under src/rag or data/docs were changed, preserving Andrii's ownership.
- Tests cover three complete API flows using a scripted model and real product persistence, plus cancellation/refund separation, tenant boundaries, stale previews, budget and allowlist.

- Increment published after 32 passing offline/API tests. User supplied an env file; it was installed only as ignored .env. GEMINI_API_KEY is present; standard MONGODB_URI was not supplied. Live provider checks are next.
## 2026-10-31 15:50: feat/support-service merged into main; final owners

- Merged origin/feat/support-service (e69ad0c) into main; TEAM-SYNC conflict resolved by keeping both sides' entries.
- Володя's area (UI + support API) is taken over by Макс (denisk0m) from scratch; we no longer wait for Володя's push.
- Final owners: Andrii = `src/rag`, `src/agent` (bridge `turn`), `src/backend` (bridge `prepare`/`execute`, seed). Макс = `src/support`, `src/ui`.
- Integration: one in-process bridge object passed to `create_app(bridge=...)`; contract 1.2 governs where older docs conflict.

- Pre-push synchronization found main 326b7a3: Andrii has taken ownership of agent/mock in parallel. Keep this implementation on feat/support-service for comparison/integration; do not overwrite his unpushed work. Preserve his owner checkpoint above.

- User clarified that Andrii did not take agent/mock ownership; Max owns this work and authorizes integrating this implementation as primary. The intermediate owner entries assigning those modules to Andrii are superseded.
- Env key was verified with a live Gemma JSON response. The hosted model intermittently returns server errors; bounded retry added. Standard MongoDB settings are absent, so local persisted product + explicit curated-file retrieval are used for the first launch.

- Updated env now supplies Gemini, Mongo writer and reader URI settings (values never logged or committed). Atlas connectivity verified: kb_global=17 and kb_tenant=11 at inspection; local Ollama is unavailable.
- Mock tenant aggregates seeded successfully in Atlas. Live Gemma promo diagnosis and confirmed resync succeeded; live promo creation also persisted a generated code.
- Live billing diagnosis returned correct cancel_duplicate_subscription with an explicit no-refund explanation. Hosted provider intermittently fails; bounded retries are enabled.
- Fetch found fe3ad52 from Andrii with alternate agent/agent.py, agent/serve.py, backend/mock_saas.py. Preserve these files and their tests; integrated runtime.py/product.py remain the user-authorized primary persisted implementation.
- Latest offline/API checks: 34 passed. Vector RAG remains unverified on this machine until Ollama embeddinggemma is available; curated-file fallback is explicit.
