# Feature docs (approach from "Розробка та підтримка продукту в еру ШІ", M. Topor, notes/ai-dev-presentation.pptx)

AI scales what already exists: with documented features every AI session writes code the way the team would.
Each feature gets `docs/features/<feature>/` with these files:

| File | What goes in |
|---|---|
| `FEATURE.md` | What and why, scope, acceptance criteria |
| `business-context.md` | Business rules, limits, policies |
| `end-to-end-flow.md` | Step-by-step flow; PO accepts the feature by reading this |
| `entry-points.json` | Code entry points (file, function, CLI) |
| `per-app-responsibility.md` | What each part (agent / rag / ui) does |
| `backend-structure.md` | Modules, data flow |
| `frontend-structure.md` | Screens/components (or "n/a") |
| `data-model.md` | Collections, schemas |
| `integration-points.md` | Overlaps with other features, contracts used |
| `known-gotchas.md` | Pitfalls found so far |

## Flow
1. **Grooming:** `feature-grooming` agent interviews the owner and drafts `FEATURE.md` + `end-to-end-flow.md`.
2. **Test cases first:** `test-cases-first` agent writes test cases from the docs; an engineer reviews them before code (green tests != right feature).
3. **Implement** against the docs.
4. **Sync:** after a code change, `feature-docs-sync` agent checks the feature docs, asks the engineer, and updates them.
5. **Accept:** the owner reads `end-to-end-flow.md`; wrong logic goes back to step 3.

Features: [rag-knowledge-base](rag-knowledge-base/FEATURE.md). Teammates: copy the file list above for `support-agent` and `support-ui`.
