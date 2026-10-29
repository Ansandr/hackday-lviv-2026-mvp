# Hack Day Lviv 2026 - MVP

PolyTech Code Fest x SKELAR, 2026-10-31, Viking Business Center (Zelena 151, Lviv).
Build 11:15-17:00 - **submission deadline 17:00** - finalist pitch 5 min + 2-3 min Q&A.
The challenge is announced at the briefing; this repo is the starter kit (Gemma helpers + docs).

## Team setup (10 min, do before Saturday)
1. `git clone <repo-url>` and `cd` into it.
2. `python -m venv .venv && .venv\Scripts\activate` (macOS/Linux: `source .venv/bin/activate`)
3. `pip install -r requirements.txt`
4. `copy .env.example .env` and put YOUR OWN Gemini API key in it (never commit or share keys).
   How to get one: [docs/SETUP.md](docs/SETUP.md) section 2B.
5. `python src/hello_gemma.py` - should print a greeting.
6. Optional offline fallback: install Ollama, `ollama pull gemma3:4b`, `python src/hello_local.py`.

## Docs
- [docs/SETUP.md](docs/SETUP.md) - Gemma models, API key, Ollama, snippets
- [docs/PLAYBOOK.md](docs/PLAYBOOK.md) - timeline and pitch outline

## Workflow
- Branch per person/feature (`feat/<name>-<thing>`), small PRs or direct pushes to `main` near the deadline; pull often.
- Never commit `.env`. Keep prompts in one file. Cache model responses for the demo.
