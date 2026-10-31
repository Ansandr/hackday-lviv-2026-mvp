# Three-scenario MVP architecture

Status: target MVP architecture, 2026-10-31. Implementation is pending.
Canonical interfaces: [CONTRACTS.md](CONTRACTS.md). Collaboration rules: [../AGENTS.md](../AGENTS.md).
The user's current scope contains exactly three scenarios: promo failure, duplicate subscription charge, and promo creation.

## Components and ownership

Use the existing Python codebase. Run FastAPI as one application with separate modules.
The mock product can run inside this application behind a service interface.
An HTTP adapter can replace that interface later without changes to agent tools.

| Component | Responsibility | Suggested owner |
|---|---|---|
| Chat UI | Messages, questions, evidence, action preview, confirmation, result | Frontend |
| API and agent | Authentication, conversation state, bounded tool loop, policy checks | Agent |
| Mock product and storage | Promo, checkout, subscription state, logs, atomic actions | Backend/DB |
| RAG | Approved documentation ingestion, embeddings, filtered retrieval | RAG |

The API owns conversation persistence. RAG does not own tickets or product writes.
The browser and model never receive database credentials.

Flow: UI -> authenticated API -> agent -> typed tool dispatcher -> mock product / RAG -> MongoDB.
All tool results return through the dispatcher. The agent explains their results to the user.

## Agent workflow

Use one agent with explicit state, not a multi-agent system.
Use the three supported intents from CONTRACTS.md.
Other requests receive a scope explanation. They do not activate additional workflows.

Conversation states and intent values are defined in CONTRACTS.md.
Limit each turn to eight tool calls, one schema-repair attempt, and a configured deadline.
Missing facts cause a question. Missing evidence causes an unresolved result, never an invented diagnosis.

The model selects reads, interprets evidence, asks questions, and proposes an allowed action.
Server code decides authorization, validates arguments, and applies mutations.
Structured model output uses a strict schema. Unknown tools and fields are rejected.

## Exact scenarios

### Promo code fails at checkout

Ask for the code and checkout or venue when these identifiers are missing.
Read the checkout event, follow its trace, then read current promo and POS state.
Seed the main case with active promo version 7 and POS version 6.
The trace contains `PROMO_CACHE_MISS`, `PROMO_LOOKUP_OK`, and `POS_SYNC_FAILED` events.
The agent cites those events and proposes `resync_pos` for that venue.
After confirmation, the mock copies current promo versions into the POS cache.
Run `validate_checkout` again. This read-only simulation never places an order or charges a card.
Only successful validation supports a resolved result.
An expired code or wrong venue receives an explanation without resynchronization.

### Duplicate subscription charge

Read captured payments, linked subscriptions, and the subscription creation trace.
Seed two subscriptions for the same tenant, business, plan, currency, and overlapping service period.
Two distinct captured payments link to those subscriptions.
Creation logs show a retried signup with missing idempotency protection.
The agent explains that evidence and identifies the newer duplicate subscription.
The server verifies the duplicate relationship and protects the retained subscription.
After confirmation, `cancel_duplicate_subscription` disables renewal on the duplicate and marks it canceled in the mock.
The action leaves the valid subscription active.
Cancellation prevents future billing. It does not refund the captured charge.
The response explicitly states that the past charge still needs a refund decision outside this MVP.
A pending authorization, separate business, or single subscription does not authorize cancellation.

### Create a promo code

Collect discount percentage, venue, start date, expiry date, and total usage limit.
Use percentage discounts only in this MVP. Validate 1 through 100 and a positive integer usage limit.
Interpret dates in the tenant timezone and store UTC instants.
The API validates that expiry follows start and that the venue belongs to the tenant.
Show a complete preview. After confirmation, `create_promo` generates the code on the server.
Use a unique tenant/code index and retry code generation on collision.
Return the stored code, constraints, and promo ID. A database write failure never produces a success reply.

## Tenant isolation and authorization

`tenant_id` identifies the SaaS customer account. `business_id` and `venue_id` belong to that account.
The API derives tenant and actor identity from a verified server session.
Demo login can use two fixed seeded accounts with server-side sessions and environment-provided credentials.
The browser cannot establish identity with an arbitrary tenant header or body field.

Every repository method requires `RequestContext(tenant_id, actor_id, role, request_id)`.
Every lookup and mutation includes `tenant_id`, including lookups by globally unique IDs.
The server verifies business, venue, conversation, trace, and action ownership.
Cross-tenant object requests return the same not-found response as unknown objects.
Only the owner role can approve mutations. A viewer can read permitted conversations and evidence.
Authorization is application-enforced. A shared MongoDB collection does not provide automatic row-level isolation.

Only the API and mock product receive write credentials. RAG retrieval uses read-only credentials.
Restrict Atlas network access to application addresses. Keep secrets outside the repository.
Do not expose raw MongoDB filters, arbitrary HTTP requests, Python execution, or shell tools to the model.
Log text, retrieved documents, and user messages are untrusted data, never execution instructions.
Delimiters and injection classifiers supplement server validation. They are not authorization controls.
Send only redacted, bounded evidence to the model. Keep tokens, payment details, and secrets out of logs.

## RAG boundary

RAG retrieves approved instructions, product rules, and known error descriptions.
Operational evidence comes from indexed log queries and current product state.
Do not embed the full operational log stream for this demo.

Keep shared product documentation in `kb_global` and tenant documents in `kb_tenant`.
Retrieve global approved records plus tenant approved records with a vector-search tenant prefilter.
Deduplication and ingestion use the same tenant boundary.
Never promote customer tickets into the global collection.
For this MVP, only curated seed documents are approved. Automatic judge-based publication is disabled.

MongoDB Vector Search supports Atlas Free clusters:
https://www.mongodb.com/docs/vector-search/deployment/deployment-options/

Embedding generation and answer generation are separate model tasks.
Voyage offers model-dependent free token allowances, not an unlimited free conversational model:
https://docs.voyageai.com/docs/pricing

Choose one embedding model and dimension for both ingestion and queries.
Changing the model requires re-embedding records and matching the vector index dimension.
Keep the existing answer-model provider behind an adapter. Verify structured-output behavior with the selected model before integration.

## Interfaces and persistence

All HTTP, agent, RAG, database, and action integrity contracts live in [CONTRACTS.md](CONTRACTS.md).
Do not duplicate those definitions here.

## Demo data and acceptance

Seed two tenants with similar codes and separate records. Seed tenant A's three happy paths and tenant B's isolation records.
Use deterministic trace IDs and realistic chronological events, not only a prewritten diagnosis field.
Keep a local reset script for seeded demo data. Do not expose reset as an agent tool or public endpoint.

Required checks:

1. Promo trace identifies stale POS data. Confirmed synchronization makes checkout validation pass.
2. Duplicate subscription cancellation preserves the valid subscription and captured payments.
3. Promo creation asks for missing fields and returns the code persisted in MongoDB.
4. Tenant A cannot read tenant B's conversations, logs, RAG records, or actions.
5. A log containing an instruction cannot activate an unlisted tool or bypass confirmation.
6. Repeated and concurrent confirmations create only one mutation and one terminal audit result.
7. Stale or expired action previews fail without a mutation.
8. Pending authorization and different-business charges never authorize duplicate cancellation.
9. Model or database failure produces an explicit failure, not a success message.

## Integration order

First agree on these contracts and example responses. Then implement the mock product and seed data.
Frontend can use the example shapes while backend work proceeds.
RAG can expose its existing retrieval function through the typed adapter.
Connect agent reads first, then proposals, confirmation, writes, and verification.
Run the acceptance checks before demo polish.
Defer auto-ingestion, quality judges, sentiment dashboards, additional venue onboarding, and refund execution.
