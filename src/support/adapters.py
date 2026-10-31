"""Replace these adapters when teammate interfaces land. No model has mutation access."""
import json
import os

import httpx

from .models import AgentResponse, Execution, Prepared


class DependencyError(Exception):
    pass


class ActionRejected(DependencyError):
    """Upstream explicitly guarantees rejection without a mutation."""


class HttpBridge:
    def __init__(self, agent_url, saas_url, key=""):
        self.agent_url, self.saas_url, self.key = agent_url, saas_url, key

    def call(self, base, path, payload, key=None):
        if not base:
            raise DependencyError("Adapter URL is not configured")
        headers = {"Authorization": f"Bearer {self.key}"}
        if key:
            headers["Idempotency-Key"] = key
        try:
            with httpx.Client(timeout=45, follow_redirects=False) as client:
                response = client.post(base.rstrip("/") + path, json=payload, headers=headers)
                if response.status_code in (403, 404, 409, 422):
                    raise ActionRejected("SaaS відхилив дію: перевірте права, дані та актуальність пропозиції")
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DependencyError("Upstream unavailable or invalid response") from exc

    def turn(self, context, conversation):
        return AgentResponse.model_validate(self.call(self.agent_url, "/turn", {"context": context.model_dump(), "conversation": conversation}))

    def prepare(self, context, proposal, evidence):
        return Prepared.model_validate(self.call(self.saas_url, "/support/actions/prepare", {"context": context.model_dump(), "proposal": proposal, "evidence": evidence}))

    def execute(self, context, action):
        return Execution.model_validate(self.call(self.saas_url, "/support/actions/execute", {"context": context.model_dump(), "action": action}, action["action_id"]))


class DemoBridge:
    """Explicit UI fixture, not an AI model or the team's mock SaaS."""
    def turn(self, context, conversation):
        text = conversation["messages"][-1]["text"].lower()
        last = conversation.get("latest_turn") or {}
        proposal = None
        questions = []
        if "рефанд" in text or "повернен" in text:
            reply = "Можу зареєструвати запит на повернення зайвого платежу. Він очікуватиме розгляду; гроші ще не повернено."
            proposal = {"type": "create_refund_request", "parameters": {"business_id": "business_01", "payment_id": "pay_02", "related_payment_id": "pay_01"}}
        elif "двічі" in text or "подвійн" in text:
            reply = "Демонстраційні дані містять дві підписки одного бізнесу. Пропоную скасувати зайву. Окремо можна подати запит на повернення коштів."
            proposal = {"type": "cancel_duplicate_subscription", "parameters": {"business_id": "business_01", "subscription_id": "sub_02", "retained_subscription_id": "sub_01"}}
        elif last.get("questions") or "створ" in text:
            try:
                parameters = json.loads(conversation["messages"][-1]["text"])
                proposal = {"type": "create_promo", "parameters": parameters}
                reply = "Перевірте параметри промокоду перед створенням."
            except ValueError:
                reply = "Для прикладу заповніть форму параметрів нижче. Демо приймає її як JSON; живий агент зможе ставити уточнення звичайною мовою."
                questions = [{"field": "promo", "prompt": "Заклад, знижка, початок, завершення та ліміт використань"}]
        elif "промокод" in text or "кас" in text:
            reply = "У демоприкладі каса має застарілі дані промокодів. Пропоную синхронізувати касу й перевірити результат."
            proposal = {"type": "resync_pos", "parameters": {"venue_id": "venue_01"}}
        else:
            reply = "Допоможу з промокодом на касі, подвійним списанням або створенням промокоду."
        return AgentResponse.model_validate({"reply": reply, "state": "needs_input" if questions else "unresolved", "questions": questions, "proposal": proposal, "evidence": [{"kind": "log", "id": "demo_fixture", "summary": "Тестовий приклад інтерфейсу, без звернення до SaaS"}] if proposal else []})

    def prepare(self, context, proposal, evidence):
        summaries = {"resync_pos": "Оновити дані каси для вибраного закладу", "cancel_duplicate_subscription": "Скасувати зайву підписку, зберігши основну", "create_promo": "Створити промокод із зазначеними умовами", "create_refund_request": "Зареєструвати запит на розгляд зайвого платежу"}
        return Prepared(summary="Демо: " + summaries[proposal["type"]], preconditions={"fixture": True}, preview={"demo": True}, evidence_ids=[e["id"] for e in evidence])

    def execute(self, context, action):
        kind = action["type"]
        after = {"demo": True, "status": "pending_review" if kind == "create_refund_request" else "simulated"}
        if kind == "create_promo":
            after["code"] = "DEMO-" + action["action_id"][-6:].upper()
        return Execution(type=kind, resource_id="demo_" + action["action_id"], before=None, after=after, verification={"demo": True, "funds_moved": False})


def configured_bridge():
    if os.getenv("SUPPORT_MODE", "remote") == "demo":
        return DemoBridge()
    return HttpBridge(os.getenv("SUPPORT_AGENT_URL", ""), os.getenv("SUPPORT_SAAS_URL", ""), os.getenv("SUPPORT_SERVICE_KEY", ""))
