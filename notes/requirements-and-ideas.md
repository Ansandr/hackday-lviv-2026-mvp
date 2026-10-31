> Historical planning reference. Current scope and rules: [AGENTS.md](../AGENTS.md). Canonical interfaces: [CONTRACTS.md](../docs/CONTRACTS.md). Conflicting ideas below are not current requirements.

# Requirements & ideas (living doc, newest decisions at the bottom of each section)

## Hard requirements (from bot / organizers)
- Event: PolyTech Code Fest x SKELAR, 31.10.2026. Team 14.
- Challenge: AI solution for **customer support** that helps solve real problems, not just answers questions.
- Judged on **value of the solution, not number of features**.
- Build window 11:15-17:00. Deadline 17:00: upload to https://drive.google.com/drive/folders/1mS3Urw7f08FKy3P9M15oklWt_hBH5OTY
- Top-15 announced 17:55; pitches 18:00-20:50 (team 14 slot: 20:00-20:50); awards 21:00.
- Mentors booked: 12:00 Orest Sonich, 13:20 Dmytro Ivasikiv (20 min each).
- Pitch: how idea came about -> problem (~30s) -> solution (~30s) -> live demo (~half the talk) -> next step. No "thank you". Freeze code 30 min before pitch; keep backup video/screenshots.
- Extra goal: nomination for best use of **Gemma** (criteria unknown, check /task slides).
- TODO: read the /task presentation in the bot and add exact judging criteria here.

## Product direction (our decisions)
- Agent **acts** (tool calls on a mock backend), not just chats. Rules/limits enforced in code, model only classifies/phrases.
- Local Gemma via Ollama (privacy, offline demo). Currently `gemma3:4b` in src/hello_local.py; verify tool calling works.
- **Feature A - input analysis**: per ticket JSON {intent, sentiment, aggression, urgency, churn_risk, is_security_threat}. Drives queue priority, reply style, escalation (code thresholds).
- **Feature B - automatic post-resolution grading** (customers rarely leave ratings): Gemma-as-judge reads dialog + action log + backend state; rubric: resolved?, action allowed by policy?, agent tone, customer sentiment delta, efficiency. Output 1-5 + reason + tags.
  - Value: ~100% coverage vs 5-10% surveys; catches agent mistakes; bad cases feed known-gotchas/few-shot; manager dashboard; policy-violation metric.
- Feedback loop: cluster tickets -> write entries to `known-gotchas.md` style doc (ties to Topor lecture: docs as context, green != right).
- Gemma used in 3 roles: tone analyst, executor, judge.

## Business candidates (pick one)
1. Dog-training subscription app (close to SKELAR portfolio): double charge, cancel, lesson won't open.
2. Kids math school: reschedule lesson, refund missed one, change tutor. Emotional parents.
3. Hosting / SaaS ("CloudNest"): site down, invoice/refund, renew domain/SSL, upgrade plan, security incident (human only). Technical + angry customers = great for tone demo. **Current favourite.**
4. Mobile operator (Vodafone / Kyivstar style): wrong charges, change plan, speed. Obvious, many teams likely do it.
5. Food delivery, 6. Car/scooter sharing (screenshots -> multimodal), 7. Travel/airline (high-stakes guardrails), 8. Fitness club (freeze/cancel), 9. Coffee loyalty app.

## DECISION (direction set)
- Business A (owner's idea): **SaaS for venues / venue chains** (1C-like, Fest Republic / Lokal-style integrations): visit stats, promo codes, staff management, P&L. Our product = support automation for this SaaS.
- Pipeline: ticket -> tone/intent analysis -> RAG over docs/known-gotchas -> agent either answers, **executes an action**, or **proposes the action to the customer** -> if bug: multi-stage checks -> dev ticket with repro. Post-resolution auto-grade.
- Business B (teammate's): supplier / warehouse idea - details to confirm with teammate, see chat evaluation.
- Tech add: **RAG + context injection step** (retrieve docs, tenant data, policies -> inject into prompt). Clarify whether "injection" also means prompt-injection defence.

### Ticket types for venue SaaS
- How-to: "how to create a promo code", "export P&L to Excel"
- Data discrepancy: "revenue today differs from POS", "visit stats are zero"
- Integration: POS/Lokal sync broken, payment terminal not syncing
- Staff: shift overlap, wrong salary calc, add/remove employee, role permissions
- Billing: double charge, change plan, invoice for accountant
- Promo: code not applied, stacking rules, expired
- Bugs: report won't load, wrong totals -> dev ticket
- Security/account: locked account, ex-employee still has access (human only)

### Who is the "customer" (alignment with team)
- Our view: customer = a **business using a SaaS**; support = that business contacting the **SaaS vendor / developers** (B2B support). Venue owner is the ticket author, the SaaS company is the support provider. We build the vendor's support layer; the SaaS itself is a mock.
- Teammates' ideas = a business supporting ITS end customers (B2C support). Different thing; not our scope.
- Pitch demo = 3 scenarios: how-to via RAG, agent action (reset sync), bug -> structured dev ticket.

### RAG ingestion ("injection") - clarified
Automated pipeline that BUILDS the RAG knowledge base from raw sources into structured records (not just chunking text):
- Sources: product docs, solved tickets, dev-ticket postmortems, policies, release notes, chat logs.
- Gemma extracts per source a structured record: {type, title, symptom, cause, resolution_steps, action_tool (if automatable), product_area, severity, source_id, date}.
- Dedup/merge similar tickets into one "known issue" entry with a counter.
- Store: SQLite (structured fields + text) + embeddings (Ollama). Retrieval = filter by product_area/type, then vector top-k; answer cites record ids.
- Loop: every resolved + graded ticket is ingested automatically -> KB grows; low-graded ones flagged for human review before entering KB.

## Open questions
- Which business? (SaaS/hosting vs kids math vs other)
- Does gemma3:4b handle tools + reliable JSON? Else bigger Gemma or JSON-mode.
- Exact judging rubric from /task.
