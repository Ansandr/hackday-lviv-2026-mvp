"""Mock venue SaaS: tenant-scoped reads for agent tools + prepare/execute for the 4 actions (CONTRACTS 1.2).

shortcut: state is in-memory (resets on restart, single process), not MongoDB; move SEED into Mongo collections if the demo needs persistence.
"""
import copy
import threading
import uuid
from datetime import datetime, timezone

from src.support.adapters import ActionRejected
from src.support.models import Execution, Prepared


def _now():
    return datetime.now(timezone.utc).isoformat()


def _tenant_seed(suffix=""):
    s = suffix
    return {
        "promos": {f"FALL20{s}": {"promo_id": f"promo_01{s}", "code": f"FALL20{s}", "venue_id": "venue_01", "discount_percent": 20,
                                  "starts_at": "2026-10-01T00:00:00Z", "expires_at": "2026-11-30T23:59:59Z", "max_redemptions": 500,
                                  "redemption_count": 41, "status": "active", "version": 7}},
        "pos_state": {"venue_01": {"venue_id": "venue_01", "promo_versions": {f"FALL20{s}": 6}, "last_sync_at": "2026-10-31T11:58:00Z", "version": 3}},
        "checkouts": {"checkout_01": {"checkout_id": "checkout_01", "business_id": "business_01", "venue_id": "venue_01", "promo_code": f"FALL20{s}",
                                      "trace_id": "trace_checkout_01", "occurred_at": "2026-10-31T12:00:05Z", "accepted": False,
                                      "rejection_code": "PROMO_UNKNOWN_ON_POS"}},
        "subscriptions": {
            "sub_01": {"subscription_id": "sub_01", "business_id": "business_01", "plan_id": "pro_monthly", "period_start": "2026-10-15",
                       "period_end": "2026-11-15", "status": "active", "renewal_enabled": True, "version": 1},
            "sub_02": {"subscription_id": "sub_02", "business_id": "business_01", "plan_id": "pro_monthly", "period_start": "2026-10-15",
                       "period_end": "2026-11-15", "status": "active", "renewal_enabled": True, "version": 1},
        },
        "payments": {
            "pay_01": {"payment_id": "pay_01", "subscription_id": "sub_01", "business_id": "business_01", "amount_minor": 99900, "currency": "UAH",
                       "status": "captured", "trace_id": "trace_billing_01"},
            "pay_02": {"payment_id": "pay_02", "subscription_id": "sub_02", "business_id": "business_01", "amount_minor": 99900, "currency": "UAH",
                       "status": "captured", "trace_id": "trace_billing_01"},
        },
        "logs": [
            {"log_id": "log_01", "trace_id": "trace_checkout_01", "parent_event_id": None, "service": "pos", "event": "PROMO_CACHE_MISS",
             "occurred_at": "2026-10-31T12:00:01Z", "entity_refs": {"venue_id": "venue_01", "checkout_id": "checkout_01"}, "safe_details": {"code": f"FALL20{s}"}},
            {"log_id": "log_02", "trace_id": "trace_checkout_01", "parent_event_id": "log_01", "service": "promo-api", "event": "PROMO_LOOKUP_OK",
             "occurred_at": "2026-10-31T12:00:02Z", "entity_refs": {"venue_id": "venue_01"}, "safe_details": {"version": 7}},
            {"log_id": "log_03", "trace_id": "trace_checkout_01", "parent_event_id": "log_02", "service": "promo-sync", "event": "POS_SYNC_FAILED",
             "occurred_at": "2026-10-31T12:00:03Z", "entity_refs": {"venue_id": "venue_01", "checkout_id": "checkout_01"},
             "safe_details": {"expected_version": 7, "actual_version": 6, "reason": "delivery_timeout"}},
            {"log_id": "log_11", "trace_id": "trace_billing_01", "parent_event_id": None, "service": "billing", "event": "SUBSCRIPTION_CREATE_RETRY",
             "occurred_at": "2026-10-15T09:00:04Z", "entity_refs": {"business_id": "business_01", "subscription_id": "sub_02"}, "safe_details": {"attempt": 2}},
        ],
        "refund_requests": {},
        "actions": {},  # action_id -> Execution dict (idempotency)
        "audit": [],
    }


SEED = {"tenant_a": _tenant_seed(), "tenant_b": _tenant_seed("B")}


class MockSaaS:
    def __init__(self, seed=SEED):
        self.db = copy.deepcopy(seed)
        self.lock = threading.Lock()

    def _t(self, ctx):
        # Tenant comes only from the server-side context; unknown tenant sees nothing.
        return self.db.get(ctx.tenant_id) or {k: type(v)() for k, v in _tenant_seed().items()}

    # ---- read tools (agent) ----
    def find_checkout(self, ctx, checkout_id=None, venue_id=None, promo_code=None):
        rows = self._t(ctx)["checkouts"].values()
        return [c for c in rows if (checkout_id and c["checkout_id"] == checkout_id)
                or (not checkout_id and (not venue_id or c["venue_id"] == venue_id) and (not promo_code or c["promo_code"].lower() == str(promo_code).lower()))]

    def get_trace(self, ctx, trace_id):
        return sorted([l for l in self._t(ctx)["logs"] if l["trace_id"] == trace_id], key=lambda l: l["occurred_at"])[:50]

    def get_promo_state(self, ctx, code, venue_id):
        t = self._t(ctx)
        promo = next((p for p in t["promos"].values() if p["code"].lower() == str(code).lower() and p["venue_id"] == venue_id), None)
        pos = t["pos_state"].get(venue_id)
        if not promo:
            return None
        return {"promo": promo, "pos_version": (pos or {}).get("promo_versions", {}).get(promo["code"])}

    def get_billing_context(self, ctx, business_id):
        t = self._t(ctx)
        subs = [s for s in t["subscriptions"].values() if s["business_id"] == business_id]
        pays = [p for p in t["payments"].values() if p["business_id"] == business_id]
        return {"subscriptions": subs, "payments": pays, "trace_ids": sorted({p["trace_id"] for p in pays})}

    def validate_checkout(self, ctx, checkout_id):
        c = self._t(ctx)["checkouts"].get(checkout_id)
        if not c:
            return None
        state = self.get_promo_state(ctx, c["promo_code"], c["venue_id"])
        ok = bool(state) and state["pos_version"] == state["promo"]["version"]
        return {"accepted": ok, "rejection_code": None if ok else "PROMO_UNKNOWN_ON_POS",
                "evaluated_version": state["pos_version"] if state else None}

    # ---- action lifecycle (support API) ----
    def _check(self, ctx, kind, p):
        """Validate eligibility from current records; return (summary, preconditions, preview). Raises ActionRejected."""
        t = self._t(ctx)
        if ctx.role != "owner":
            raise ActionRejected("forbidden")
        if kind == "resync_pos":
            pos = t["pos_state"].get(p["venue_id"])
            if not pos:
                raise ActionRejected("unknown venue")
            stale = {c: v for c, v in pos["promo_versions"].items() if t["promos"].get(c, {}).get("version") != v}
            return (f"Синхронізувати касу закладу {p['venue_id']}", {"pos_version": pos["version"]},
                    {"venue_id": p["venue_id"], "stale_promos": stale})
        if kind == "cancel_duplicate_subscription":
            a, b = t["subscriptions"].get(p["subscription_id"]), t["subscriptions"].get(p["retained_subscription_id"])
            if not a or not b or a is b or a["business_id"] != p["business_id"] or b["business_id"] != p["business_id"]:
                raise ActionRejected("invalid subscriptions")
            if a["status"] != "active" or b["status"] != "active" or a["plan_id"] != b["plan_id"] or a["period_start"] != b["period_start"]:
                raise ActionRejected("not a duplicate")
            return (f"Скасувати дублікат підписки {a['subscription_id']}, залишити {b['subscription_id']}", {"version": a["version"]},
                    {"cancel": a["subscription_id"], "keep": b["subscription_id"], "plan_id": a["plan_id"]})
        if kind == "create_promo":
            if p["venue_id"] not in t["pos_state"]:
                raise ActionRejected("unknown venue")
            return (f"Створити промокод -{p['discount_percent']}% для {p['venue_id']}", {}, {**p})
        if kind == "create_refund_request":
            pay, rel = t["payments"].get(p["payment_id"]), t["payments"].get(p["related_payment_id"])
            if not pay or not rel or pay is rel or pay["business_id"] != p["business_id"] or rel["business_id"] != p["business_id"]:
                raise ActionRejected("invalid payments")
            if pay["status"] != "captured" or rel["status"] != "captured" or (pay["amount_minor"], pay["currency"]) != (rel["amount_minor"], rel["currency"]):
                raise ActionRejected("not a duplicate charge")
            s1, s2 = t["subscriptions"].get(pay["subscription_id"]), t["subscriptions"].get(rel["subscription_id"])
            if not s1 or not s2 or s1["plan_id"] != s2["plan_id"] or s1["period_start"] > s2["period_end"] or s2["period_start"] > s1["period_end"]:
                raise ActionRejected("periods do not overlap")
            preview = {"payment_id": pay["payment_id"], "amount_minor": pay["amount_minor"], "currency": pay["currency"],
                       "reason": "suspected_duplicate_charge", "review_required": True}
            return (f"Запит на повернення {pay['amount_minor'] / 100:.2f} {pay['currency']} (платіж {pay['payment_id']}), потребує розгляду",
                    {"payment_status": "captured", "amount_minor": pay["amount_minor"]}, preview)
        raise ActionRejected("unknown action")

    def prepare(self, ctx, proposal, evidence):
        with self.lock:
            summary, pre, preview = self._check(ctx, proposal["type"], proposal["parameters"])
        return Prepared(summary=summary, preconditions=pre, preview=preview, evidence_ids=[e["id"] for e in evidence])

    def execute(self, ctx, action):
        kind, p, aid = action["type"], action["parameters"], action["action_id"]
        with self.lock:
            t = self._t(ctx)
            if aid in t["actions"]:  # idempotent replay with the same action ID
                return Execution(**t["actions"][aid])
            _, pre, _ = self._check(ctx, kind, p)
            if pre != action.get("preconditions", pre):
                raise ActionRejected("stale preconditions")
            if kind == "resync_pos":
                pos = t["pos_state"][p["venue_id"]]
                before = copy.deepcopy(pos)
                pos["promo_versions"] = {c: t["promos"][c]["version"] for c in pos["promo_versions"] if c in t["promos"]}
                pos["last_sync_at"], pos["version"] = _now(), pos["version"] + 1
                for c in t["checkouts"].values():  # re-validation now passes for this venue
                    if c["venue_id"] == p["venue_id"]:
                        c["accepted"], c["rejection_code"] = True, None
                res = dict(resource_id=p["venue_id"], before=before, after=copy.deepcopy(pos),
                           verification={"resolved": all(t["promos"][c]["version"] == v for c, v in pos["promo_versions"].items())})
            elif kind == "cancel_duplicate_subscription":
                sub = t["subscriptions"][p["subscription_id"]]
                before = copy.deepcopy(sub)
                sub.update(status="canceled", renewal_enabled=False, version=sub["version"] + 1)
                res = dict(resource_id=sub["subscription_id"], before=before, after=copy.deepcopy(sub),
                           verification={"resolved": False, "persisted": t["subscriptions"][p["subscription_id"]]["status"] == "canceled"})
            elif kind == "create_promo":
                code = "PROMO" + uuid.uuid4().hex[:6].upper()
                promo = {"promo_id": "promo_" + uuid.uuid4().hex[:8], "code": code, **p, "starts_at": str(p["starts_at"]),
                         "expires_at": str(p["expires_at"]), "redemption_count": 0, "status": "active", "version": 1}
                t["promos"][code] = promo
                res = dict(resource_id=promo["promo_id"], before=None, after=promo, verification={"resolved": code in t["promos"], "persisted": True})
            else:
                existing = t["refund_requests"].get(p["payment_id"])  # unique (tenant, payment_id)
                if existing:
                    res = dict(resource_id=existing["refund_request_id"], before=existing, after=existing,
                               verification={"persisted": True, "funds_moved": False})
                else:
                    pay = t["payments"][p["payment_id"]]
                    rr = {"refund_request_id": "rr_" + uuid.uuid4().hex[:8], "business_id": p["business_id"], "payment_id": p["payment_id"],
                          "related_payment_id": p["related_payment_id"], "amount_minor": pay["amount_minor"], "currency": pay["currency"],
                          "reason": "suspected_duplicate_charge", "status": "pending_review", "actor_id": ctx.actor_id,
                          "conversation_id": action.get("conversation_id"), "action_id": aid, "evidence_ids": action.get("evidence_ids", [])}
                    t["refund_requests"][p["payment_id"]] = rr
                    res = dict(resource_id=rr["refund_request_id"], before=None, after=rr,
                               verification={"persisted": p["payment_id"] in t["refund_requests"], "funds_moved": False})
            out = {"type": kind, **res}
            t["actions"][aid] = out
            t["audit"].append({"audit_id": "aud_" + uuid.uuid4().hex[:8], "action_id": aid, "actor_id": ctx.actor_id, "event": kind,
                               "before": res["before"], "after": res["after"], "occurred_at": _now()})
            return Execution(**out)
