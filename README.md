# Hack Day Lviv 2026 - MVP: AI support layer for a venue SaaS

PolyTech Code Fest x SKELAR, 2026-10-31. Build 11:15-17:00 - **submission deadline 17:00** - finalist pitch 5 min + 2-3 min Q&A.

**What we build:** an AI support desk for a SaaS company whose customers are venue owners (cafes, chains).
The owner writes to support; the AI answers from the knowledge base (RAG), runs an action in the SaaS,
or proposes a step to the owner; real bugs go to developers as structured tickets. Every closed ticket is
auto-graded. The SaaS itself is a mock. Full brief: [docs/CONTRACTS.md](docs/CONTRACTS.md), [notes/requirements-and-ideas.md](notes/requirements-and-ideas.md).

Demo scenarios: (1) how to create a promo code, (2) connect a second venue, (3) promo code not applied at the POS, (4) double subscription charge.

## Who owns what
| Area | Owner | Folder |
|---|---|---|
| Mock SaaS, agent loop, tools, policy rules | A | `src/agent/` |
| RAG: ingestion, MongoDB vector store, retrieval, tone, judge | Andrii (B) | `src/rag/`, `data/` |
| Chat UI, dev/quality pages, demo, pitch | C | `src/ui/` |

Interfaces between parts are fixed in [docs/CONTRACTS.md](docs/CONTRACTS.md). Change them only after telling the team.

## Team setup
1. `git clone https://github.com/Ansandr/hackday-lviv-2026-mvp` and `cd` into it.
2. `python -m venv .venv && .venv\Scripts\activate` (macOS/Linux: `source .venv/bin/activate`)
3. `pip install -r requirements.txt`
4. `copy .env.example .env` and put YOUR OWN keys in it (never commit or share keys).
5. `python src/hello_gemma.py` - should print a greeting. Offline: Ollama + `python src/hello_local.py`.

## Workflow
- Work only in your own folder; shared files (`docs/CONTRACTS.md`, `requirements.txt`, `README.md`) - announce in chat before editing.
- Branch `feat/<name>-<thing>`, push often, merge to `main` after a quick look from a teammate. After 16:00 - direct pushes to `main`, `git pull --rebase` before every push.
- Until a teammate's part is ready, use a stub that returns data in the contract shape.
- Never commit `.env`. Keep prompts in one file per area. Cache model responses for the demo.

## Docs
- [docs/CONTRACTS.md](docs/CONTRACTS.md) - data shapes between agent, RAG and UI
- [docs/SETUP.md](docs/SETUP.md) - Gemma models, API key, Ollama, snippets
- [docs/PLAYBOOK.md](docs/PLAYBOOK.md) - timeline and pitch outline
- [notes/rag-plan.md](notes/rag-plan.md) - RAG design, MongoDB, security
