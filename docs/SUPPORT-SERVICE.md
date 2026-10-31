# Run the support service

The support frontend and API live in `src/ui/` and `src/support/`.
They do not replace the team's agent, RAG, or mock SaaS implementation.
Canonical request shapes and adapter boundaries: [CONTRACTS.md](CONTRACTS.md).

## Local UI demonstration

From the repository root, install requirements and run:

```powershell
python -m pip install -r requirements.txt
$env:SUPPORT_MODE = "demo"
python -m uvicorn src.support.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and use access code `demo-a` or `demo-b`.
Demo mode is explicit. It uses deterministic fixture responses, not a model, and never changes SaaS data.
The promo parameter form sends sample JSON only in this fixture mode.
The real agent can collect the same fields through ordinary language questions.
SQLite preserves conversations, action previews, results, audit records, and hashed session tokens across restarts.
The database file is ignored by Git. It is separate from the product's MongoDB state.

## Connect the team components

Use `support.env.example` for variable names. Provide real local values in `.env`.

```powershell
$env:SUPPORT_MODE = "remote"
python -m uvicorn src.support.app:app --env-file .env --port 8000
```

Install `python-dotenv` from requirements to use `--env-file`.
Configure SUPPORT_ACCOUNTS with private access codes and server-owned tenant/actor/role mappings.
The API exchanges the access code for an eight-hour bearer session. The browser keeps it in sessionStorage.
No browser tenant header is trusted. Bearer authentication does not use cookies, so cookie CSRF does not apply.
Keep the UI same-origin. Use HTTPS when exposing the service outside localhost.

`HttpBridge` calls the agent for conversational turns. The agent reads RAG and mock SaaS through its own allowed tools.
When the agent returns a proposal, the API asks the SaaS adapter to validate and prepare it.
Only the confirm route can call the SaaS executor. Browser parameters cannot replace the stored preview.
The four action variants, payloads, and upstream routes are defined only in CONTRACTS.md.

For an in-process agent or Vолодя's Python mock, replace `HttpBridge` with an object implementing `turn`, `prepare`, and `execute`.
Pass it to `create_app(bridge=...)`; the frontend and routes stay the same.
The app accepts `create_app(store=..., bridge=..., accounts=...)` for integration tests and alternative persistence adapters.

Remote mode never falls back to fixture responses. Missing adapters or invalid responses return a dependency error.
Health reports application availability and mode, not upstream readiness. An integration test must verify the real dependencies.

## Scope and limitations

Run exactly one API worker for this MVP. A process-wide lock serializes changes while SQLite persists state.
The support service cannot share a database transaction with a remote SaaS.
The SaaS executor must atomically store its mutation, idempotency result, and product audit in its own MongoDB transaction.
A timeout keeps the local action `executing`. Confirm again to reconcile with the same action ID.
Never repeat an uncertain action with a new ID. The remote executor must return its stored result for the old ID.
The support audit is a local receipt; the SaaS audit is authoritative for product mutations.
Approval expires after ten minutes. A new turn invalidates the previous unconfirmed preview.
An executing action blocks new turns until reconciliation.
Cancellation and refund requests keep the conversation unresolved. Refund submission never means funds were returned.
The agent and SaaS endpoints are trusted server components; they must enforce the evidence and resource checks documented in CONTRACTS.md.

Tests:

```powershell
python -m pytest tests/test_support.py -q
```

Use `/docs` for the generated API reference. The browser UI supports history, evidence, questions, four action cards, rejection, and results.
