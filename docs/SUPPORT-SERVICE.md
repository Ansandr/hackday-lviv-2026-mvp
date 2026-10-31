# First integrated launch

The app now includes the Gemma agent and a persistent mock SaaS. Run from the repository root:

```powershell
python -m pip install -r requirements.txt
./start-support.ps1
```

The launcher loads `.env`, seeds the two tenant accounts without resetting existing product state, and prints temporary login codes when SUPPORT_ACCOUNTS is absent.
Open http://127.0.0.1:8000. Set SUPPORT_PORT to use another port.
No built-in fixed login code exists in integrated mode.

At least one model connection is required:

- Hosted: set GEMINI_API_KEY in local `.env`; GEMMA_MODEL selects the model.
- Local: start Ollama, pull gemma3:4b, set SUPPORT_LLM=local and LOCAL_MODEL=gemma3:4b.

No model credentials or Ollama are currently configured on Max's checked machine. Live model completion is therefore pending.
Do not paste keys into Git. Add them only to `.env`.

The launcher defaults explicitly to SUPPORT_PRODUCT_STORE=sqlite and SUPPORT_RAG_MODE=files for independent startup.
Those choices provide real persisted mock-product actions and local curated-doc lookup, without MongoDB or embedding dependencies.
They do not simulate an AI response: the conversational agent still requires Gemma.
To use the shared services, set SUPPORT_PRODUCT_STORE=mongo, MONGODB_URI, MONGODB_DB, SUPPORT_RAG_MODE=atlas, and ensure Andrii's ingestion/indexes and Ollama embeddinggemma are ready.
The RAG module is unchanged. Its vector-search integration requires a live check against the team's actual database.

Try these scenarios:

1. "Промокод AUTUMN20 не проходить на касі venue_01". Inspect evidence, confirm sync, verify resolved checkout.
2. "З нас двічі списали гроші за підписку business_01". Confirm cancellation of the duplicate; then ask to create a refund request. The request awaits review.
3. "Створи промокод для venue_01: знижка 15%, з сьогодні до 31 грудня 2026, максимум 50 використань". Review dates and parameters before confirming.

Reset only mock product state for another demo:

```powershell
$env:SUPPORT_PRODUCT_STORE = "sqlite"
python -m src.backend.seed --reset
```

Old action previews become stale after reset/version changes; create a new conversation.
Use seed reset only outside an active execution. Existing support history is retained.

Verified locally: all three API flows with a scripted model and real local product persistence. A scripted model verifies wiring, not Gemma reasoning quality.
Live Gemma and shared Atlas validation remain pending until credentials and dependencies are configured.

# Additional modes and adapters

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
