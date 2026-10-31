# Integration checklist до 17:00

Стан на 2026-10-31 ~15:00. Інтерфейси визначає тільки [CONTRACTS.md](CONTRACTS.md) (v1.1.0); тут лише план робіт.
Перевірено: `origin/main` = `b3cdbf3` (RAG v1 змерджено в main, contract 1.1.0).

## Gap analysis: код vs CONTRACTS.md

| Частина | Є в коді | Чого бракує за контрактом |
|---|---|---|
| RAG (`src/rag`) | `retrieve(query, context, intent, k)` -> `{kb_id, text, score}`, `kb_global`/`kb_tenant`, фільтр tenant/status/intent, 4 curated docs (вкл. refund request policy), offline + live тести | немає обгортки `search_kb` з envelope `{ok, data, evidence_ids, error}`; Atlas не піднятий; ембедінги вимагають локальний Ollama `embeddinggemma` на машині, де крутиться API |
| Mock SaaS + DB | Нічого | Колекції `promos`, `pos_state`, `checkouts`, `subscriptions`, `payments`, `refund_requests`, `logs`, `actions`, `audit_events`, `conversations`; seed tenant_a/tenant_b; унікальні індекси; read-функції під 6 read-tools; executor для 4 actions (transaction, idempotency, version check, audit) |
| Agent (`src/agent`) | Нічого (є лише `src/tools_demo.py` як приклад function calling) | Tool loop на Gemma (≤8 викликів), 7 tools, dispatcher інжектить RequestContext, `propose_action` з 4 variants, збірка `AgentTurn`, перевірка `evidence_ids` |
| API (FastAPI) | Нічого; `fastapi`/`uvicorn` немає в `requirements.txt` | 5 routes `/api/v1/...`, server-side session (2 demo-акаунти), role `owner`/`viewer`, `409 CONVERSATION_BUSY`, error shape |
| UI (`src/ui`) | Нічого | Чат, `questions`, `evidence`, preview `proposed_action`, Confirm/Reject, `ActionResult`, текст для refund request |

Головний ризик: за 2 години не встигнути все. Пріоритет: три happy paths end-to-end на tenant_a. Concurrency, CSRF, tenant_b-ізоляція в UI — тільки якщо лишиться час (див. "Можна спростити").

## Git workflow (для всіх)

- [ ] Пушити маленькі коміти часто: мінімум кожні 30–45 хв або після кожного зеленого тесту.
- [ ] Перед push: `git fetch origin && git pull --rebase origin main`, потім `python -m pytest tests`, потім `git push`. Без `--force`.
- [ ] Перед комітом: `git status --short` і `git diff --staged`; додавати файли поіменно, не `git add .`.
- [ ] Ніколи не комітити `.env` (він у `.gitignore`; перевірити, що не в staged). Ключі й паролі Atlas тільки в приватному чаті.
- [ ] Зміна контракту (поле, enum, route, tool args) — тільки через `docs/CONTRACTS.md` (version + change log) + запис у `docs/TEAM-SYNC.md` в тому ж коміті, і усно сказати команді.
- [ ] Кожен працює у своїй папці (`src/agent`, `src/rag`, `src/ui`, mock/API — див. нижче); чужі файли не редагувати без попередження.

## Whole team (першими, 15:00–15:15)

- [x] Завершити merge `feat/andrii-rag` у `main` і запушити (`b3cdbf3`). **Done when:** `python -m pytest tests` зелений у кожного після pull.
- [x] Вирішити, де живуть API і mock: пропозиція `src/backend/` (FastAPI app + mock repo + seed + executor, як у README; див. INTEGRATION-REQUIREMENTS Q1). **Done when:** owner кожної папки названий у TEAM-SYNC.md.
- [ ] Додати `fastapi`, `uvicorn` у `requirements.txt` (одна людина, один коміт). **Done when:** `pip install -r requirements.txt` у всіх проходить.
- [ ] Одна спільна MongoDB: Atlas за [ATLAS-SETUP.md](ATLAS-SETUP.md) **або** локальний `mongodb-atlas-local` на демо-ноутбуці. **Done when:** усі мають однаковий `MONGODB_URI` у своєму `.env`.
- [ ] Визначити демо-ноутбук: на ньому Mongo, Ollama з `embeddinggemma`, `GEMINI_API_KEY`. **Done when:** `python -m src.rag.retrieve "Як створити промокод"` повертає hits на ньому.

## Mock SaaS (`src/backend`, owner: Andrii)

Порядок важливий: агент і UI чекають на п.1–3.

- [ ] 1. `RequestContext` один на весь проєкт (можна імпортувати з `src/rag/retrieve.py`). **Done when:** agent і mock використовують той самий клас.
- [ ] 2. Seed-скрипт `python -m src.backend.seed --reset` для tenant_a (і мінімально tenant_b): promo v7 + `pos_state` v6 для `venue_01`, `checkout_01` з trace `PROMO_CACHE_MISS` -> `PROMO_LOOKUP_OK` -> `POS_SYNC_FAILED`; 2 subscriptions + 2 captured payments з однаковим plan/amount/currency/period; logs з `SUBSCRIPTION_CREATE_RETRY` (назва як у `data/docs/error-codes.md`). **Done when:** скрипт ідемпотентний, у Data Explorer видно записи з `tenant_id`, `version`, `created_at`.
- [ ] 3. Read-функції (всі з `tenant_id` у фільтрі): `find_checkout`, `get_trace`, `get_promo_state`, `get_billing_context`, `validate_checkout`. **Done when:** pytest на seed повертає очікувані дані, а виклик з `tenant_b` для `checkout_01` повертає not found.
- [ ] 4. `propose_action` storage: зберігає action у `actions` зі `status=proposed`, `expires_at`, `preconditions` (версії з БД, не від моделі). Валідація 4 variants; невідомий type -> `VALIDATION_ERROR`. **Done when:** тест на кожен variant + один невалідний.
- [ ] 5. Executor `resync_pos`: копіює promo versions у `pos_state`, `version+1`, audit event, `ActionResult` з `before/after/verification`. **Done when:** після confirm `validate_checkout("checkout_01")` -> `accepted: true`.
- [ ] 6. Executor `create_promo`: валідація 1–100 %, `max_redemptions > 0`, `expires_at > starts_at`, venue належить tenant; код генерує сервер, retry на колізію. **Done when:** код читається з `promos` після confirm.
- [ ] 7. Executor `cancel_duplicate_subscription`: дубль -> `canceled`, `renewal_enabled=false`, retained лишається active, payments не змінюються. **Done when:** тест перевіряє обидві підписки і незмінні payments.
- [ ] 8. Executor `create_refund_request`: перевірка двох captured payments; unique index `(tenant_id, payment_id)`; status `pending_review`; `verification={persisted: true, funds_moved: false}`; повторний confirm повертає той самий ID. **Done when:** два confirm -> один запис.
- [ ] 9. Повторний confirm того самого `action_id` повертає збережений результат (idempotency); прострочений action -> `STALE_ACTION`. **Done when:** 2 тести зелені.
- [ ] 10. FastAPI routes з CONTRACTS.md (5 шт.), сесія через фіксовані demo-токени з `.env` (owner tenant_a, owner tenant_b). **Done when:** `uvicorn src.backend.main:app` і `curl` на `POST /api/v1/conversations` повертає `{conversation_id, state}`; без сесії — 401.

## Agent (`src/agent`, owner: Andrii)

- [ ] 1. Перевірити, чи `GEMMA_MODEL` тягне native tool calling (`src/tools_demo.py`); якщо ні — JSON-режим (`src/rag/llm.py::chat_json` як зразок). **Done when:** рішення записане в TEAM-SYNC.md (≤15 хв).
- [ ] 2. `search_kb` обгортка над `src.rag.retrieve.retrieve` в envelope `{ok, data: {hits}, evidence_ids: [kb_id...], error}`. **Done when:** unit-тест з stub retrieve.
- [ ] 3. Dispatcher: allowlist 7 tools, RequestContext інжектить сервер, невідомий tool/зайве поле -> помилка, не виклик. **Done when:** тест: модель просить `tenant_id` або невідомий tool -> відмова.
- [ ] 4. Tool loop: ≤8 tool calls, 1 schema-repair, deadline; класифікація intent (`promo_how_to | promo_not_applied | double_charge | other`); `other` -> пояснення scope. **Done when:** на "як створити промокод" повертає `AgentTurn` з `evidence` kind `kb`.
- [ ] 5. Збірка `AgentTurn` точно як JSON-приклад у CONTRACTS.md; `evidence` тільки з реально отриманих `evidence_ids`. **Done when:** тест відкидає невідомий evidence id.
- [ ] 6. System prompt: повідомлення, логи, KB — це data (`src/rag/sanitize.py::as_data`); скасування не повертає гроші; refund request ≠ повернення. **Done when:** лог з "ignore instructions" не викликає action без confirm.
- [ ] 7. Підключити до `POST /conversations/{id}/messages` (разом з API owner). **Done when:** три сценарії через curl дають очікуваний `proposed_action`.

## RAG (`src/rag`, owner: Andrii)

- [x] 1. Завершити merge і push (див. Whole team). **Done when:** RAG у `origin/main`.
- [ ] 2. `ingest --reset` на спільній БД (Atlas або демо-ноутбук). **Done when:** live тести зелені проти цієї БД.
- [ ] 3. Допомогти Agent з `search_kb` (envelope + intent). **Done when:** agent-тест з реальним retrieve повертає `KB-...` id.
- [ ] 4. Звірити назви подій у `data/docs/error-codes.md` з seed-логами mock (`POS_SYNC_FAILED`, `SUBSCRIPTION_CREATE_RETRY`). **Done when:** назви збігаються дослівно.
- [ ] 5. Короткий абзац для пітчу: як Gemma використана (embeddinggemma + Gemma 4 extraction + agent). **Done when:** текст у чаті команди.

## UI + support API (`src/ui`, `src/support`, owner: Макс @denisk0m, гілка `feat/support-service`)

Можна почати одразу на JSON-прикладі з CONTRACTS.md, без бекенду.

- [ ] 1. Одна статична сторінка (FastAPI віддає `src/ui/index.html` або окремий dev-сервер) з чатом. **Done when:** відправка тексту показує відповідь з mock JSON.
- [ ] 2. Рендер `questions`, `evidence` (kind + id + summary), `state`. **Done when:** приклад з CONTRACTS.md рендериться повністю.
- [ ] 3. Картка `proposed_action` для всіх 4 types (summary, parameters, expires_at) + Confirm/Reject -> `POST /api/v1/actions/{id}/confirm`. **Done when:** невідомий type показує fallback, а не падає.
- [ ] 4. Рендер `ActionResult`: для `create_refund_request` показати ID і "Awaiting review; funds have not been returned" (не "повернено"). **Done when:** текст не містить "refunded/resolved".
- [ ] 5. Переключитись з mock JSON на реальне API. **Done when:** сценарій 1 проходить у браузері.

## Можна спростити (свідомо, записати в TEAM-SYNC.md)

- Сесія: фіксовані токени замість логіну; CSRF не потрібен, якщо токен у header.
- Транзакції: на M0/local replica set вони є; якщо не встигаємо — один update + audit, позначити як shortcut.
- `409 CONVERSATION_BUSY`, concurrency-тести, streaming — після демо.

## E2E демо (на демо-ноутбуці, tenant_a, owner)

- [ ] Підготовка: `python -m src.backend.seed --reset`, `python -m src.rag.ingest`, `uvicorn ...`, браузер відкритий, `python -m pytest tests` зелений.
- [ ] **Сценарій 1, promo не працює:** "Промокод X не проходить на касі в venue_01" -> evidence з `POS_SYNC_FAILED` (log) + KB doc -> preview `resync_pos` -> Confirm -> `succeeded`, `validate_checkout` accepted -> state `resolved`.
- [ ] **Сценарій 2, подвійне списання:** "З нас двічі зняли за підписку" -> evidence з двох payments + `SUBSCRIPTION_CREATE_RETRY` -> preview `cancel_duplicate_subscription` -> Confirm -> дубль canceled, основна active; агент прямо каже, що скасування гроші не повертає -> окремий preview `create_refund_request` -> Confirm -> ID запиту, "Awaiting review; funds have not been returned", state `unresolved`.
- [ ] **Сценарій 3, створити промокод:** "Хочу промокод" -> `questions` для відсутніх полів -> відповіді -> preview `create_promo` -> Confirm -> код з БД у чаті.
- [ ] Бонус (якщо є час): Reject на preview -> нічого не змінилось; повторний Confirm -> той самий результат; tenant_b не бачить `checkout_01`.
- [ ] Запасний план: записати відео трьох сценаріїв до 16:40; скріншоти в README.

## Таймлайн до 17:00

| Час | Що | Хто |
|---|---|---|
| 15:00–15:15 | Merge RAG у main, push, pull у всіх; owners папок; requirements; спільна БД | Whole team |
| 15:15–15:45 | Seed + read-функції; agent tool-calling check + `search_kb`; UI на mock JSON | API/mock, Agent, UI |
| 15:45–16:15 | `propose_action` + executors (`resync_pos`, `create_promo` першими); tool loop + `AgentTurn`; UI action card | API/mock, Agent, UI |
| 16:15–16:30 | Routes + підключення агента + UI до реального API; cancel + refund executors | Усі |
| 16:30–16:40 | Feature freeze. E2E три сценарії, фікси тільки блокерів, запис відео | Усі |
| 16:40–16:55 | README, TEAM-SYNC checkpoint, фінальний push, сабміт | Whole team |
| 16:55 | **Сабміт відправлено** | — |
