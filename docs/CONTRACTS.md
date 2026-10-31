# Canonical MVP contracts

Contract version: **1.0.0**. Date: 2026-10-31.
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

`propose_action` accepts only three discriminated variants:

```text
resync_pos: {venue_id}
cancel_duplicate_subscription: {business_id, subscription_id, retained_subscription_id}
create_promo: {venue_id, discount_percent, starts_at, expires_at, max_redemptions}
```

The server constructs preconditions from current records. It does not trust model-supplied versions or duplicate classifications.
Execution is a server operation reached through authenticated confirmation, not a model-accessible tool.

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
| logs | log_id, trace_id, parent_event_id, service, event, occurred_at, entity_refs, safe_details |
| actions | action_id, conversation_id, actor_id, type, parameters, preconditions, status, expires_at, result |
| audit_events | audit_id, action_id, actor_id, event, before, after, occurred_at |
| kb_tenant | kb_id, title, text, embedding, embedding_model, intent, status |
| kb_global | kb_id, title, text, embedding, embedding_model, intent, status; no customer-derived content |

Unique indexes: `(tenant_id, resource_id)` on each tenant collection, `(tenant_id, code)` on promos, `(tenant_id, venue_id)` on pos_state.
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
| 1.0.0 | 2026-10-31 | Consolidate three-scenario API, agent, RAG, DB, and action contracts; supersede the initial sketch | Explicit user request in this Codex chat; repository notice in TEAM-SYNC.md; no external message sent | Direct merge authorized; implementation migration pending |

For each later change, record the before/after behavior, compatibility, affected owners, migration, and notification reference before implementation.
No PR or owner acknowledgment is required during the hackathon. Publish notices for all contract changes, including optional additions.
Integrate with current main, preserve teammate work, and document unresolved implementation migrations.
