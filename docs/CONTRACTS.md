# Canonical MVP contracts

Contract version: **1.2.0**. Date: 2026-10-31.
Status: user-directed target baseline. Direct integration is authorized. This file and TEAM-SYNC.md publish the change notice.

This file is the single source of truth for frontend, agent, RAG, mock product, and database interfaces.
The specification does not imply that these interfaces are implemented.
Read [../AGENTS.md](../AGENTS.md) for mandatory change and synchronization rules.
Architecture rationale belongs in [ARCHITECTURE.md](ARCHITECTURE.md), not in a second contract file.

## Shared types and ownership

The API owns conversation persistence and authenticates every request.
RequestContext contains server-derived tenant_id, actor_id, role, and request_id strings.
Role is `owner | viewer`. Only owners can approve mutations.
Intent is `promo_how_to | promo_not_applied | double_charge | other`.
`other` returns a scope explanation without executing a workflow.
Conversation state is `investigating | needs_input | awaiting_confirmation | executing | resolved | unresolved`.
New clients use conversation state. The old ticket status enum is retired.
AgentTurn is the response shape in the frontend example below. All shown top-level fields are required.
Message is `{message_id, role, text, created_at}` with role `user | assistant`.
The server creates message IDs and timestamps. `messages` in a stored conversation contains Message objects.
`latest_turn` is null until the first AgentTurn exists.
ActionResult and tool errors use the shared error shape documented below.

## RAG module interface

`retrieve(query, context, intent=None, k=4) -> list[KbHit]`
The dispatcher supplies RequestContext. The model supplies only query and optional intent.
Reject k outside 1 through 10. Retrieve only approved global and authenticated-tenant documents.
KbHit is `{kb_id, text, score}`. kb_id and text are strings. score is a retrieval relevance number, not a confidence probability.
The search_kb tool wraps this function in the standard tool-result envelope.
Ingestion writes tenant documents only within their tenant boundary. Global documents contain curated product material only.
Automatic publication from tickets or judge scores is disabled in this MVP.

## Frontend API v1

These routes define the target MVP interface. Implementation is pending. Previous interfaces require the migration described below.
All routes require a session. Mutation requests require CSRF protection when cookie authentication is used.
All timestamps use ISO 8601 UTC strings. IDs are opaque strings. Money uses integer minor units and a currency.

| Route | Request | Response |
|---|---|---|
| POST /api/v1/conversations | `{}` | `{conversation_id, state}` |
| POST /api/v1/conversations/{id}/messages | `{client_message_id, text}` | `AgentTurn` |
| GET /api/v1/conversations/{id} | none | `{conversation_id, state, messages, latest_turn}` |
| POST /api/v1/actions/{id}/confirm | `{decision: "confirm" or "reject"}` | `ActionResult` |
| GET /api/v1/actions/{id} | none | `ActionResult` |

Use ordinary JSON requests for the MVP. Streaming is optional and does not change these shapes.
Deduplicate messages using `(tenant_id, conversation_id, client_message_id)`.
Serialize turns within a conversation and reject a conflicting turn with `409 CONVERSATION_BUSY`.

```json
{
  "schema_version": "1",
  "conversation_id": "conv_01",
  "state": "awaiting_confirmation",
  "reply": "The POS has an older promo version. Confirm synchronization.",
  "questions": [],
  "evidence": [
    {"kind": "log", "id": "log_03", "summary": "POS synchronization failed"},
    {"kind": "kb", "id": "KB-PROMO-003", "summary": "POS synchronization procedure"}
  ],
  "proposed_action": {
    "action_id": "act_01",
    "type": "resync_pos",
    "parameters": {"venue_id": "venue_01"},
    "summary": "Synchronize promo data for venue_01",
    "expires_at": "2026-10-31T13:05:00Z"
  },
  "action_result": null
}
```

`questions` contains `{field, prompt, options?: string[]}` objects. `proposed_action` can be null.
Evidence summaries come from authorized records. The UI never shows model reasoning or hidden prompts.
`ActionResult` contains `{action_id, status, result, error}`.
Status: `proposed | rejected | expired | executing | succeeded | failed`.
`result` is null before success. On success it contains `{type, resource_id, before, after, verification}`.
`error` is null or `{code, message, retryable, request_id}`.
Common errors: `NOT_FOUND`, `FORBIDDEN`, `VALIDATION_ERROR`, `STALE_ACTION`, `MODEL_UNAVAILABLE`, `DEPENDENCY_UNAVAILABLE`.
The API uses HTTP 401, 403, 404, 409, 422, and 503 as appropriate.

## Agent tool contracts

The dispatcher injects RequestContext. The model never supplies or overrides it.
Each result contains `{ok, data, evidence_ids, error}`. Unknown evidence IDs cannot appear in a final response.

| Tool | Model arguments | Data |
|---|---|---|
| search_kb | query, intent | hits: kb_id, text, score |
| find_checkout | checkout_id? or venue_id + promo_code + time window | matching checkout summaries |
| get_trace | trace_id | bounded ordered log events |
| get_promo_state | code, venue_id | rules, current version, POS version |
| get_billing_context | business_id | subscriptions, payments, related trace IDs |
| validate_checkout | checkout_id | accepted, rejection_code, evaluated_version |
| propose_action | type, parameters, evidence_ids | stored action preview |

`propose_action` accepts only these four discriminated variants:

```text
resync_pos: {venue_id}
cancel_duplicate_subscription: {business_id, subscription_id, retained_subscription_id}
create_promo: {venue_id, discount_percent, starts_at, expires_at, max_redemptions}
create_refund_request: {business_id, payment_id, related_payment_id}
```

The server constructs preconditions from current records. It does not trust model-supplied versions or duplicate classifications.
Execution is a server operation reached through authenticated confirmation, not a model-accessible tool.

## Refund request within double_charge

The agent can propose `create_refund_request` for a suspected duplicate captured charge supported by payment and log evidence.
This action registers a request for review. It never calls a payment provider or changes a payment to refunded.
Cancellation and refund requests are independent actions with separate previews and confirmations.
Declining cancellation does not prevent a refund request. An already canceled subscription can still have a captured payment.

The server verifies two distinct captured payments belonging to the same tenant and business.
It verifies matching plan, currency, amount, and overlapping service periods through linked subscriptions.
Both payments can belong to one subscription. That case permits a refund request, but not duplicate-subscription cancellation.
A pending authorization, already refunded payment, or unrelated payment fails validation.
Unclear evidence causes clarification, not automatic approval of a refund.

The server derives amount_minor and currency from the target payment and stores evidence_ids from the validated proposal.
The MVP requests the full target payment amount. Partial refunds are outside scope.
The preview displays the target payment, amount, currency, reason, and the fact that review is required.
The server snapshots these values in action preconditions and revalidates them on confirmation.

A confirmed action creates one `refund_requests` record with status `pending_review` and reason `suspected_duplicate_charge`.
Use a unique `(tenant_id, payment_id)` index to prevent duplicate requests, including requests from different conversations.
If a request already exists, return its ID and current status without creating another request.
Use a transaction for request creation, action result, and audit. Payment and subscription states remain unchanged.
On a concurrent unique-key conflict, reread the existing request and persist the action result without another request.

ActionResult uses type `create_refund_request` and resource_id equal to refund_request_id.
Its after object contains refund_request_id, payment_id, amount_minor, currency, and status `pending_review`.
Its verification object contains `{persisted: true, funds_moved: false}` after a successful read-back.
For a new request before is null. For an existing request before and after contain the same request summary.
A succeeded action means that the request was registered, not that a refund succeeded.
The chat shows the request ID and "Awaiting review; funds have not been returned".
Keep conversation state `unresolved` while the financial issue awaits review. Action success does not resolve the charge itself.
No refund approval or processing endpoint is part of this MVP.

## MongoDB contracts

Every tenant record contains `tenant_id`, an opaque resource ID, `created_at`, and `updated_at`.
Mutable product records also contain `version`, an integer used for optimistic concurrency.

| Collection | Required domain fields |
|---|---|
| conversations | conversation_id, actor_id, state, messages, latest_turn |
| promos | promo_id, code, venue_id, discount_percent, starts_at, expires_at, max_redemptions, redemption_count, status |
| pos_state | venue_id, promo_versions, last_sync_at |
| checkouts | checkout_id, business_id, venue_id, promo_code, trace_id, occurred_at |
| subscriptions | subscription_id, business_id, plan_id, period_start, period_end, status, renewal_enabled |
| payments | payment_id, subscription_id, business_id, amount_minor, currency, status, trace_id |
| refund_requests | refund_request_id, business_id, payment_id, related_payment_id, amount_minor, currency, reason, status, actor_id, conversation_id, action_id, evidence_ids |
| logs | log_id, trace_id, parent_event_id, service, event, occurred_at, entity_refs, safe_details |
| actions | action_id, conversation_id, actor_id, type, parameters, preconditions, status, expires_at, result |
| audit_events | audit_id, action_id, actor_id, event, before, after, occurred_at |
| kb_tenant | kb_id, title, text, embedding, embedding_model, intent, status |
| kb_global | kb_id, title, text, embedding, embedding_model, intent, status; no customer-derived content |

Unique indexes: `(tenant_id, resource_id)` on each tenant collection, `(tenant_id, code)` on promos, `(tenant_id, venue_id)` on pos_state.
Refund requests additionally require a unique `(tenant_id, payment_id)` index. The only request status in this MVP is `pending_review`.
Read indexes: logs `(tenant_id, trace_id, occurred_at)`, subscriptions `(tenant_id, business_id)`, payments `(tenant_id, business_id)`.
Vector index filter fields: tenant_id, status, intent. Global documents use a separate vector index without tenant_id.

Example sanitized event:

```json
{
  "tenant_id": "tenant_a",
  "log_id": "log_03",
  "trace_id": "trace_checkout_01",
  "parent_event_id": "log_02",
  "service": "promo-sync",
  "event": "POS_SYNC_FAILED",
  "occurred_at": "2026-10-31T12:00:00Z",
  "entity_refs": {"venue_id": "venue_01", "checkout_id": "checkout_01"},
  "safe_details": {"expected_version": 7, "actual_version": 6, "reason": "delivery_timeout"}
}
```

## Action integrity

An action ID identifies immutable parameters, tenant, actor, conversation, evidence, and resource-version preconditions.
Confirmation cannot replace action parameters. Editing a preview creates a new action and invalidates the old one.
At confirmation, revalidate the session, role, expiry, ownership, and current resource versions.
Use the action ID as the idempotency key. Repeated confirmation returns the stored result.
Use a MongoDB transaction for the mock mutation, action result, and audit event.
Inside the transaction, compare status and resource versions before writing.
A crash before commit leaves no mutation. A crash after commit permits retrieval of the stored result.
Concurrent confirmations can commit at most one mutation.
The mock has no external payment effects, so all its writes can share that transaction.
Verify the result with a subsequent read. Report a verification failure without repeating a successful mutation.

## Migration from the initial sketch

This baseline replaces the original unversioned docs/CONTRACTS.md at commit 3439040.
The old definitions remain in Git history, not as a competing specification.

| Previous sketch | Canonical v1 decision | Affected owners |
|---|---|---|
| Ticket stored by RAG | API-owned conversations and Message objects | API, RAG, frontend |
| Browser-provided tenant_id | Server-derived RequestContext | All |
| Analysis with tone and risk scores | Three supported intents plus other; tone analysis deferred | Agent, RAG |
| retrieve(query, tenant_id, product_area, k) | retrieve(query, context, intent, k) | Agent, RAG |
| Agent result with actions and judge fields | AgentTurn, action preview, and ActionResult | Agent, frontend |
| venue_connect | Outside MVP scope | All |
| Judge-approved automatic ingestion | Curated approved seed documents only | RAG |

Consumers must implement v1 or use an explicit adapter during migration. Do not silently mix the old and new shapes.

## Contract change log

| Version | Date | Change | Authorization / notification | Integration status |
|---|---|---|---|---|
| 1.1.0 | 2026-10-31 | Add confirmed refund-request registration within double_charge; no money movement | Explicit user request; repository notice in TEAM-SYNC.md | Specification only; API, agent, frontend, DB, and RAG policy updates required |
| 1.0.0 | 2026-10-31 | Consolidate three-scenario API, agent, RAG, DB, and action contracts; supersede the initial sketch | Explicit user request in this Codex chat; repository notice in TEAM-SYNC.md; no external message sent | Direct merge authorized; implementation migration pending |

For each later change, record the before/after behavior, compatibility, affected owners, migration, and notification reference before implementation.
No PR or owner acknowledgment is required during the hackathon. Publish notices for all contract changes, including optional additions.
Integrate with current main, preserve teammate work, and document unresolved implementation migrations.

### 1.1 integration notice

Existing routes and payload fields remain unchanged. The action union gains create_refund_request.
Update exhaustive action validators and UI renderers before the agent emits this new variant.
Backend adds refund_requests and its unique indexes. RAG policy must distinguish request registration from refund execution.
The existing three actions retain their behavior. New behavior remains unimplemented until the corresponding code and checks are added.

## Support service adapter boundary (1.2)

User-directed topology: separate support frontend/API -> agent -> mock SaaS reads.
Support confirmation -> SaaS executor applies the action. The agent still cannot execute mutations.
The independent service is src/support/app.py; its static frontend is src/ui/.
Existing /api/v1 conversation and action routes retain their shapes.
Action previews add optional `preview: object` containing SaaS-validated display facts such as refund amount and currency.
Stored messages may include optional `turn: AgentTurn` so history can render evidence and action results.

Additional support routes:

| Route | Request | Response |
|---|---|---|
| POST /api/v1/session | {token: string} | {access_token, expires_at, identity: {tenant_id, actor_id, role}} |
| DELETE /api/v1/session | none | {ok: true} |
| GET /api/v1/conversations | none | [{conversation_id, title, state, updated_at}] |
| GET /api/v1/health | none | {status: ok, mode: demo or remote} |

The browser supplies Authorization: Bearer session-token. Server config maps login codes to identities.
Login credentials come from SUPPORT_ACCOUNTS, never from a browser-provided identity.
Demo-only credentials are demo-a and demo-b. Remote mode has no built-in login credentials.
Sessions expire after eight hours. Action previews expire after ten minutes.

### Agent adapter

`turn(context, conversation) -> AgentResponse`; HTTP adapter: POST SUPPORT_AGENT_URL/turn.
Request is {context: RequestContext, conversation: stored conversation without message-deduplication records}.
AgentResponse is {reply: string, state, questions: Question[], evidence: Evidence[], proposal: null or {type, parameters}}.
state is investigating, needs_input, unresolved, or resolved. Proposal uses the existing four action variants.
Question and Evidence retain the frontend shapes. The agent must return only evidence from authorized tool results.
The agent does not generate action IDs, expiry, preconditions, execution results, or tenant identity.
The API validates the response and creates an awaiting_confirmation turn when proposal is present.

### SaaS adapter for action lifecycle

`prepare(context, proposal, evidence) -> Prepared`; HTTP: POST SUPPORT_SAAS_URL/support/actions/prepare.
Request is {context, proposal, evidence}. Prepared is {summary: string, preconditions: object, preview: object, evidence_ids: string[]}.
Prepare is read-only: it checks ownership, evidence, eligibility, resource versions, and derives refund amount/currency.
It must reject unauthorized resources, stale facts, invalid duplicate relationships, and unknown evidence.
The API verifies evidence_ids are a subset of supplied evidence and stores the immutable validated preview.
No product mutations happen at preparation.

`execute(context, action) -> Execution`; HTTP: POST SUPPORT_SAAS_URL/support/actions/execute.
Request is {context, action: stored action including parameters, preconditions, actor_id, conversation_id, evidence_ids, action_id}.
Execution is {type, resource_id, before: object or null, after: object, verification: object}.
Verification includes resolved:true only after an actual successful product read-back.
Refund requests require persisted:true, funds_moved:false, and after.status=pending_review.
API forces refund/cancellation conversations unresolved regardless of a model or executor resolution claim.
Both adapter services receive a shared Authorization: Bearer SUPPORT_SERVICE_KEY over a trusted transport.
Never expose these mutation endpoints as unauthenticated public model tools.
Execute also receives Idempotency-Key equal to action_id. The SaaS must durably deduplicate and revalidate preconditions atomically.
It must support replay/reconciliation with the same action ID after a lost response.

Support state currently uses SQLite, behind Store, for independent startup. Product and RAG state remain MongoDB.
This supersedes the initial assumption that all modules share one process and transaction.
SaaS mutation/result/audit remain one product transaction. Support receipts are separate persistent records.
One support API worker is supported; per-process serialization is not a distributed lock.
Unknown execution outcomes stay executing and are reconciled using the same ID, never reissued with a new ID.

Contract change notice 1.2.0 (2026-10-31): user explicitly requested independent support frontend/backend.
Affected: agent owner implements turn; SaaS owner implements prepare/execute adapters; frontend consumes optional preview and history turns.
Existing four action parameter shapes and public confirmation requests are unchanged.
HTTP bridge paths are an adapter proposal for team integration, not a claim that the colleagues' services already expose them.
Runtime details and launch commands: SUPPORT-SERVICE.md. No external team messages were sent.
