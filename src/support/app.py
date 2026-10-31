"""Run: python -m uvicorn src.support.app:app --port 8000 (one worker)."""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from .adapters import ActionRejected, DependencyError, DemoBridge, ModelUnavailable, configured_bridge
from .models import Context, Decision, Login, MessageInput, ResolutionFeedback
from .store import Store
from .triage import assess, PRIORITY_ORDER
from typing import Literal
from .tickets import Tickets, parse_resolution


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


def identifier(prefix):
    return prefix + "_" + uuid4().hex


def fail(status, code, message):
    raise HTTPException(status, {"code": code, "message": message, "retryable": status == 503})


def create_app(store=None, bridge=None, accounts=None, notifier=None):
    app = FastAPI(title="Venue Support API", version="1.2.0")
    store = store or Store(os.getenv("SUPPORT_DB", "support.sqlite3"))
    bridge = bridge or configured_bridge()
    if accounts is None:
        accounts = json.loads(os.getenv("SUPPORT_ACCOUNTS", "{}"))
        if isinstance(bridge, DemoBridge) and not accounts:
            accounts = {"demo-a": {"tenant_id": "tenant_a", "actor_id": "owner_a", "role": "owner"}, "demo-b": {"tenant_id": "tenant_b", "actor_id": "owner_b", "role": "owner"}}
    app.state.store, app.state.bridge = store, bridge
    tickets=Tickets(store,notifier)

    @app.middleware("http")
    async def headers(request, call_next):
        request.state.request_id = identifier("req")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def errors(request, exc):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail), "retryable": False}
        return JSONResponse(status_code=exc.status_code, content={"error": {**detail, "request_id": request.state.request_id}})

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "Перевірте поля запиту", "retryable": False, "request_id": request.state.request_id}})

    def context(request: Request):
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ") if auth.startswith("Bearer ") else ""
        digest = hashlib.sha256(token.encode()).hexdigest()
        session = store.get("session", digest, "sessions") if token else None
        if not session or datetime.fromisoformat(session["expires_at"]) <= now():
            fail(401, "UNAUTHENTICATED", "Увійдіть у сервіс підтримки")
        return Context(**session["identity"], request_id=request.state.request_id)

    def owned(kind, key, ctx):
        record = store.get(kind, key, ctx.tenant_id)
        if not record:
            fail(404, "NOT_FOUND", "Запис не знайдено")
        return record

    def save_conversation(c, ctx):
        c["updated_at"] = stamp()
        store.put("conversation", c["conversation_id"], ctx.tenant_id, c)

    def ask_resolution(c,turn,ask):
        prompt={'prompt_id':identifier('feedback'),'question':'Чи вдалося вирішити вашу проблему?'} if ask else None
        turn['resolution_prompt']=prompt;c['resolution_prompt']=prompt

    def update_ticket_card(c,summary,ctx):
        for message in c['messages']:
            turn=message.get('turn') or {}
            if (turn.get('support_ticket') or {}).get('ticket_id')==summary['ticket_id']:turn['support_ticket']=summary
        if ((c.get('latest_turn') or {}).get('support_ticket') or {}).get('ticket_id')==summary['ticket_id']:c['latest_turn']['support_ticket']=summary
        save_conversation(c,ctx)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "mode": "demo" if isinstance(bridge, DemoBridge) else getattr(bridge, 'mode', 'remote')}

    @app.post("/api/v1/session")
    def login(body: Login):
        identity = next((value for key, value in accounts.items() if secrets.compare_digest(key.encode(), body.token.encode())), None)
        if not identity:
            fail(401, "UNAUTHENTICATED", "Невірний код доступу")
        identity = Context(**identity, request_id="login").model_dump(exclude={"request_id"})
        token = secrets.token_urlsafe(40)
        expires = (now() + timedelta(hours=8)).isoformat()
        store.put("session", hashlib.sha256(token.encode()).hexdigest(), "sessions", {"identity": identity, "expires_at": expires})
        return {"access_token": token, "expires_at": expires, "identity": identity}

    @app.delete("/api/v1/session")
    def logout(request: Request, ctx=Depends(context)):
        digest = hashlib.sha256(request.headers["Authorization"].removeprefix("Bearer ").encode()).hexdigest()
        store.put("session", digest, "sessions", {"identity": ctx.model_dump(exclude={"request_id"}), "expires_at": stamp()})
        return {"ok": True}

    @app.get("/api/v1/conversations")
    def conversations(sort: Literal['recent','priority']='recent',ctx=Depends(context)):
        rows=[{**{k: c[k] for k in ("conversation_id", "title", "state", "updated_at")},'analysis':c.get('analysis')} for c in store.list("conversation", ctx.tenant_id)]
        if sort=='priority': rows.sort(key=lambda row:PRIORITY_ORDER.get((row.get('analysis') or {}).get('priority'),2))
        return rows

    @app.post("/api/v1/conversations", status_code=201)
    def create_conversation(ctx=Depends(context)):
        c = {"conversation_id": identifier("conv"), "actor_id": ctx.actor_id, "title": "Нове звернення", "state": "investigating", "messages": [], "latest_turn": None, "created_at": stamp(), "updated_at": stamp(), "requests": {}}
        save_conversation(c, ctx)
        return {"conversation_id": c["conversation_id"], "state": c["state"]}

    @app.get("/api/v1/conversations/{conversation_id}")
    def get_conversation(conversation_id: str, ctx=Depends(context)):
        c = owned("conversation", conversation_id, ctx)
        return {k: v for k, v in c.items() if k not in ('requests','feedback_responses')}

    @app.post("/api/v1/conversations/{conversation_id}/messages")
    def message(conversation_id: str, body: MessageInput, ctx=Depends(context)):
        if not body.text.strip():
            fail(422, "VALIDATION_ERROR", "Повідомлення порожнє")
        # One-process serialization keeps turns, confirmation and persistence ordered.
        with store.lock:
            c = owned("conversation", conversation_id, ctx)
            cached = c["requests"].get(body.client_message_id)
            if cached:
                if cached["text"] != body.text:
                    fail(409, "VALIDATION_ERROR", "ID повідомлення вже використано для іншого тексту")
                return cached["turn"]
            previous = (c.get("latest_turn") or {}).get("proposed_action")
            if previous and owned("action", previous["action_id"], ctx)["status"] == "executing":
                fail(409, "CONVERSATION_BUSY", "Спочатку перевірте результат попередньої дії")
            feedback=parse_resolution(body.text) if c.get('resolution_prompt') else None
            if feedback is not None:
                prompt_id=c['resolution_prompt']['prompt_id']
                resolution_feedback(conversation_id,ResolutionFeedback(prompt_id=prompt_id,resolved=feedback[0],comment=feedback[1]),ctx)
                c=owned('conversation',conversation_id,ctx)
                for m in c['messages']:
                    if m['message_id']=='feedback_user_'+prompt_id:m['text']=body.text
                turn=c['latest_turn']
                c['requests'][body.client_message_id]={'text':body.text,'turn':turn}
                save_conversation(c,ctx)
                return turn
            candidate = {**c, "messages": c["messages"] + [{"message_id": identifier("msg"), "role": "user", "text": body.text, "created_at": stamp()}]}
            # Triage is available even if the hosted model is temporarily down.
            c['analysis']=assess(candidate['messages']).model_dump()
            candidate['analysis']=c['analysis']
            if c['title']=='Нове звернення': c['title']=body.text[:64]
            save_conversation(c,ctx)
            public = {k: v for k, v in candidate.items() if k not in ('requests','feedback_responses')}
            try:
                response = bridge.turn(ctx, public)
                action = None
                if response.proposal:
                    proposal = response.proposal.model_dump(mode="json")
                    evidence = [e.model_dump() for e in response.evidence]
                    prepared = bridge.prepare(ctx, proposal, evidence)
                    if not set(prepared.evidence_ids).issubset({e["id"] for e in evidence}):
                        raise DependencyError("Unverified evidence")
                    action = {"action_id": identifier("act"), **proposal, "summary": prepared.summary, "expires_at": (now() + timedelta(minutes=10)).isoformat(), "preview": prepared.preview}
                    record = {**action, "conversation_id": conversation_id, "actor_id": ctx.actor_id, "preconditions": prepared.preconditions, "evidence_ids": prepared.evidence_ids, "status": "proposed", "result": None, "error": None}
                    store.put("action", action["action_id"], ctx.tenant_id, record)
            except ActionRejected:
                fail(422, "VALIDATION_ERROR", "Пропозиція не пройшла перевірку SaaS. Уточніть дані звернення.")
            except ModelUnavailable:
                fail(503, "MODEL_UNAVAILABLE", "AI-сервіс тимчасово не відповідає. Повідомлення залишилось у чаті. Натисніть «Повторити».")
            except (DependencyError, ValidationError):
                fail(503, "DEPENDENCY_UNAVAILABLE", "Агент або SaaS недоступний. Повторіть повідомлення.")
            # A new proposal invalidates any previous unconfirmed preview.
            if previous:
                old = owned("action", previous["action_id"], ctx)
                if old["status"] == "executing":
                    fail(409, "CONVERSATION_BUSY", "Спочатку перевірте результат попередньої дії")
                if old["status"] == "proposed":
                    old["status"] = "expired"
                    store.put("action", old["action_id"], ctx.tenant_id, old)
            analysis=assess(candidate['messages'],response.customer_tone).model_dump()
            turn = {"schema_version": "1", "conversation_id": conversation_id, "state": "awaiting_confirmation" if action else response.state, "reply": response.reply, "questions": [q.model_dump(exclude_none=True) for q in response.questions], "evidence": [e.model_dump() for e in response.evidence], "proposed_action": action, "action_result": None,'analysis':analysis}
            c['analysis']=analysis
            ask_resolution(c,turn,not action and not response.questions and (response.state=='resolved' or bool(response.evidence)))
            c["messages"] = candidate["messages"] + [{"message_id": identifier("msg"), "role": "assistant", "text": response.reply, "created_at": stamp(), "turn": turn}]
            c["latest_turn"], c["state"] = turn, turn["state"]
            c["title"] = body.text[:64] if c["title"] == "Нове звернення" else c["title"]
            c["requests"][body.client_message_id] = {"text": body.text, "turn": turn}
            save_conversation(c, ctx)
            return turn

    def action_result(a):
        return {k: a[k] for k in ("action_id", "status", "result", "error")}

    @app.get("/api/v1/actions/{action_id}")
    def get_action(action_id: str, ctx=Depends(context)):
        return action_result(owned("action", action_id, ctx))

    @app.post("/api/v1/actions/{action_id}/confirm")
    def confirm(action_id: str, body: Decision, ctx=Depends(context)):
        if ctx.role != "owner":
            fail(403, "FORBIDDEN", "Підтверджувати дії може лише власник")
        with store.lock:
            a = owned("action", action_id, ctx)
            if a["actor_id"] != ctx.actor_id:
                fail(403, "FORBIDDEN", "Дію створив інший користувач")
            if a["status"] in ("succeeded", "failed", "rejected", "expired"):
                return action_result(a)
            if a["status"] == "executing" and body.decision == "reject":
                fail(409, "CONVERSATION_BUSY", "Виконання вже почалось")
            if a["status"] == "proposed" and datetime.fromisoformat(a["expires_at"]) <= now():
                a["status"] = "expired"
            elif body.decision == "reject":
                a["status"] = "rejected"
            else:
                a["status"] = "executing"
                store.put("action", action_id, ctx.tenant_id, a)
                try:
                    result = bridge.execute(ctx, a).model_dump(mode="json")
                    if result["type"] != a["type"]:
                        raise DependencyError("Action result type mismatch")
                    if a["type"] == "create_refund_request" and not isinstance(bridge, DemoBridge):
                        if result["after"].get("status") != "pending_review" or result["verification"].get("funds_moved") is not False or result["verification"].get("persisted") is not True:
                            raise DependencyError("Invalid refund-request verification")
                    a["status"], a["result"] = "succeeded", result
                    a["error"] = None
                except ActionRejected:
                    a["status"] = "failed"
                    a["error"] = {"code": "STALE_ACTION", "message": "SaaS відхилив виконання. Запросіть нову перевірку та пропозицію.", "retryable": False, "request_id": ctx.request_id}
                except (DependencyError, ValidationError):
                    # Outcome may be unknown after network timeout. Retry only with the same idempotency key.
                    a["error"] = {"code": "DEPENDENCY_UNAVAILABLE", "message": "Результат ще невідомий. Повторна перевірка використає той самий ID дії.", "retryable": True, "request_id": ctx.request_id}
                    store.put("action", action_id, ctx.tenant_id, a)
                    fail(503, "DEPENDENCY_UNAVAILABLE", a["error"]["message"])
            store.put("action", action_id, ctx.tenant_id, a)
            store.put("audit", action_id, ctx.tenant_id, {"action_id": action_id, "actor_id": ctx.actor_id, "status": a["status"], "result": a["result"], "occurred_at": stamp()})
            c = owned("conversation", a["conversation_id"], ctx)
            succeeded = a["status"] == "succeeded"
            is_demo = isinstance(bridge, DemoBridge)
            verified = succeeded and a["result"]["verification"].get("resolved") is True
            state = "resolved" if verified and not is_demo and a["type"] not in ("create_refund_request", "cancel_duplicate_subscription") else "unresolved"
            text = "Дію відхилено." if a["status"] == "rejected" else "Пропозиція застаріла. Надішліть нове повідомлення."
            if a["status"] == "failed":
                text = a["error"]["message"]
            if succeeded:
                text = "Демонстрацію виконано. Дані SaaS не змінювалися." if is_demo else "Дію виконано. Перегляньте результат перевірки."
                if a["type"] == "create_refund_request":
                    text += f" Запит {a['result']['resource_id']} очікує розгляду. Гроші ще не повернено."
                if a["type"] == "cancel_duplicate_subscription":
                    text += " Скасування підписки не повертає попередній платіж. Можете попросити створити запит на повернення коштів."
                if a["type"] == "create_promo" and a["result"]["after"].get("code"):
                    text += " Промокод: " + str(a["result"]["after"]["code"])
            turn = {"schema_version": "1", "conversation_id": c["conversation_id"], "state": state, "reply": text, "questions": [], "evidence": [], "proposed_action": None, "action_result": action_result(a),'analysis':c.get('analysis')}
            ask_resolution(c,turn,a['status'] in ('succeeded','failed'))
            c["messages"].append({"message_id": identifier("msg"), "role": "assistant", "text": text, "created_at": stamp(), "turn": turn})
            c["latest_turn"], c["state"] = turn, state
            save_conversation(c, ctx)
            return action_result(a)

    @app.post('/api/v1/conversations/{conversation_id}/feedback')
    def resolution_feedback(conversation_id:str,body:ResolutionFeedback,ctx=Depends(context)):
        with store.lock:
            c=owned('conversation',conversation_id,ctx)
            responses=c.setdefault('feedback_responses',{})
            cached=responses.get(body.prompt_id)
            if cached:
                if cached['resolved']!=body.resolved or cached['comment']!=body.comment:
                    fail(409,'FEEDBACK_ALREADY_RECORDED','Відповідь на це запитання вже збережена')
            else:
                if not c.get('resolution_prompt') or c['resolution_prompt']['prompt_id']!=body.prompt_id:
                    fail(409,'STALE_FEEDBACK','Це запитання вже не актуальне. Перевірте останню відповідь.')
                ticket=None if body.resolved else tickets.build(ctx,c,body.prompt_id,body.comment,bridge)
                cached={'resolved':body.resolved,'comment':body.comment,'ticket_id':ticket['ticket_id'] if ticket else None,'completed':False}
                responses[body.prompt_id]=cached
                c['resolution_prompt']=None
                save_conversation(c,ctx)
            ticket=owned('ticket',cached['ticket_id'],ctx) if cached['ticket_id'] else None
            if not cached['completed']:
                if ticket:tickets.deliver(ticket)
                pending_refund=any(a['conversation_id']==conversation_id and a['type']=='create_refund_request' and a['status']=='succeeded' for a in store.list('action',ctx.tenant_id))
                state='resolved' if body.resolved and not pending_refund else 'unresolved'
                if body.resolved:
                    reply='Дякую за підтвердження! Радий, що допомогли.'
                    if pending_refund:reply+=' Запит на повернення коштів ще очікує розгляду; гроші поки не повернено.'
                else:
                    reply=f"Створив тікет {ticket['ticket_id']} з описом і діагностикою. Команда підтримки зможе продовжити перевірку."
                    if tickets.summary(ticket)['delivery']['status']=='sent':reply+=' Тікет надіслано в Telegram.'
                    else:reply+=' Тікет збережено; статус надсилання в Telegram показано нижче.'
                turn={'schema_version':'1','conversation_id':conversation_id,'state':state,'reply':reply,'questions':[],'evidence':[],'proposed_action':None,'action_result':None,'analysis':c.get('analysis'),'resolution_prompt':None,'support_ticket':tickets.summary(ticket) if ticket else None}
                c['messages'].append({'message_id':'feedback_user_'+body.prompt_id,'role':'user','text':('Так, проблему вирішено.' if body.resolved else 'Ні, проблему не вирішено.')+(' '+body.comment if body.comment else ''),'created_at':stamp()})
                c['messages'].append({'message_id':'feedback_bot_'+body.prompt_id,'role':'assistant','text':reply,'created_at':stamp(),'turn':turn})
                c['state']=state;c['latest_turn']=turn;cached['completed']=True
                c['customer_resolution']={'resolved':body.resolved,'prompt_id':body.prompt_id,'created_at':stamp()}
                save_conversation(c,ctx)
            return {'resolved':cached['resolved'],'ticket':tickets.summary(ticket) if ticket else None,'state':c['state']}

    @app.get('/api/v1/tickets/{ticket_id}')
    def get_ticket(ticket_id:str,ctx=Depends(context)):
        ticket=owned('ticket',ticket_id,ctx)
        return {**{k:v for k,v in ticket.items() if k!='delivery'},'delivery':tickets.summary(ticket)['delivery']}

    @app.post('/api/v1/tickets/{ticket_id}/delivery')
    def retry_ticket_delivery(ticket_id:str,ctx=Depends(context)):
        if ctx.role!='owner':fail(403,'FORBIDDEN','Повторне надсилання доступне власнику')
        with store.lock:
            ticket=owned('ticket',ticket_id,ctx)
            summary=tickets.deliver(ticket)
            c=owned('conversation',ticket['conversation_id'],ctx)
            update_ticket_card(c,summary,ctx)
            return summary

    ui = Path(__file__).resolve().parents[1] / "ui"
    app.mount("/assets", StaticFiles(directory=ui), name="assets")

    @app.get("/")
    def index():
        return FileResponse(ui / "index.html")

    return app


app = create_app()
