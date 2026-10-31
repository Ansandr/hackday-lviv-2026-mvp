---
name: push-often
description: Commit and push small, safe increments to main so the team always has current context. Use after every green test, finished checklist item, contract/doc change, or at least every 30-45 minutes; also when the user says "push", "sync", "запуш".
---

# Push often (hackathon flow)

Goal: teammates (and their agents) always see your latest work on `origin/main`. Small pushes, no surprises.

## When
- After each green `python -m pytest tests` or each finished item in docs/INTEGRATION-CHECKLIST.md.
- After any change to docs/CONTRACTS.md (in the same commit as a docs/TEAM-SYNC.md note).
- At least every 30-45 minutes, even if work is partial but not broken (keep it behind a flag or unused).

## Steps
1. Another Claude session may share this checkout: run `git status`. If a merge/rebase is in progress (`.git/MERGE_HEAD`, `.git/rebase-merge`) that you did not start, stop and ask; do not commit over it.
2. `git fetch` then `git pull --rebase origin main`. Resolve conflicts by keeping both sides' intent; never drop a teammate's change.
3. `python -m pytest tests` (offline tests must pass; live tests may be skipped if no Mongo/Ollama).
4. Stage only your files by path (`git add src/<yours> docs/...`). Never `git add -A`. Never stage `.env`.
5. One-line commit message: `<area>: <what>` (areas: rag, agent, backend, ui, docs, contracts).
6. `git push origin main`. If rejected, repeat from step 2. Never force-push main.
7. If you also keep a feature branch, fast-forward it: `git push origin main:<branch>` only when it has no unique commits.

## Never
- Commit secrets, `.env`, large binaries, or generated DB dumps.
- Change contract shapes without the TEAM-SYNC note.
- Push a red test suite to main.
