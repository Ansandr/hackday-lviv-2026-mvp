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
- Owner acknowledgment: pending before integration of the breaking baseline.

## Prepared team notice

The MVP scope is now three scenarios: promo failure, duplicate subscription charge, and promo creation.
Read AGENTS.md first. docs/CONTRACTS.md is the canonical interface and database specification.
The previous Ticket/Analysis/Agent result/Judge sketch is superseded by the v1 contracts.
Conversation persistence belongs to the API. Automatic judge-based KB publication is outside the MVP.
Frontend, agent, backend, and RAG owners must review the migration notes before integration.
Further contract changes require advance notice. Breaking changes require affected owners' acknowledgment before merge.

## Checkpoint format

For later entries, record the date, inspected remote commit, changed components, compatibility findings, checks, and unresolved coordination items.
Reference actual commits or PRs. Do not describe uncommitted teammate work as integrated.
