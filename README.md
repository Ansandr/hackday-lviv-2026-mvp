# Hack Day Lviv 2026 - MVP: AI support layer for a venue SaaS

PolyTech Code Fest x SKELAR, 2026-10-31. Build 11:15-17:00 - **submission deadline 17:00** - finalist pitch 5 min + 2-3 min Q&A.

**Start here:** [AGENTS.md](AGENTS.md) contains the shared scope and collaboration rules.
[docs/CONTRACTS.md](docs/CONTRACTS.md) is the single canonical contract.
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains the target design.
[docs/TEAM-SYNC.md](docs/TEAM-SYNC.md) records observed implementation and coordination status.

We build a support agent for venue owners using a mock SaaS.
The MVP covers exactly three scenarios: promo code failure at checkout, duplicate subscription charge, and promo creation.
The agent reads evidence, asks questions, proposes an action, and verifies the persisted result after confirmation.
The repository contains RAG and an independent support UI/API on the support-service branch. Gemma agent and persisted mock SaaS are connected in integrated mode; live model credentials are required.
Start with `./start-support.ps1`. Run the support service using [docs/SUPPORT-SERVICE.md](docs/SUPPORT-SERVICE.md).

## Work boundaries

| Area | Suggested location | Responsibility |
|---|---|---|
| API and agent | src/agent/ | Sessions, conversations, tool dispatch, policy |
| Mock product and DB | src/backend/ | Product state, logs, mutations, audit |
| RAG | src/rag/, data/ | Curated documents, embeddings, tenant-filtered retrieval |
| Frontend | src/ui/ | Chat, questions, evidence, action confirmation |

These are module boundaries, not confirmed person assignments. Existing ownership remains subject to team coordination.

## Team setup
1. `git clone https://github.com/Ansandr/hackday-lviv-2026-mvp` and `cd` into it.
2. `python -m venv .venv && .venv\Scripts\activate` (macOS/Linux: `source .venv/bin/activate`)
3. `pip install -r requirements.txt`
4. `copy .env.example .env` and put YOUR OWN keys in it (never commit or share keys).
5. `python src/hello_gemma.py` - should print a greeting. Offline: Ollama + `python src/hello_local.py`.

## Workflow

Follow [AGENTS.md](AGENTS.md). Inspect remote changes at task start, before integration and commit, and every 30 minutes during active work.
Direct pushes to main are authorized during the hackathon. Preserve teammate changes. Record meaningful synchronization in docs/TEAM-SYNC.md.
Publish contract change notices in the repository. No PR review or owner acknowledgment is required before merge.
Keep contract definitions only in docs/CONTRACTS.md. Other files link to it.
Never commit .env or secrets.

## Supporting references

- [docs/SETUP.md](docs/SETUP.md): provider setup examples.
- [docs/PLAYBOOK.md](docs/PLAYBOOK.md): event planning reference.
- [notes/](notes/): historical ideas, superseded where they conflict with the canonical context.
