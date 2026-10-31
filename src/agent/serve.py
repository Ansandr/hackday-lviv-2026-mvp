"""Live demo entry point: support API + UI wired in-process to the Gemma agent and mock SaaS.

Run: python -m uvicorn src.agent.serve:app --port 8000   (login codes from SUPPORT_ACCOUNTS, default demo-a / demo-b)
"""
import json
import os

from src.backend.mock_saas import MockSaaS
from src.support.app import create_app

from .agent import Agent


class LocalBridge:
    """turn -> agent, prepare/execute -> mock SaaS. Same interface as HttpBridge/DemoBridge."""
    def __init__(self, saas=None, agent=None):
        self.saas = saas or MockSaaS()
        self.agent = agent or Agent(self.saas)

    def turn(self, context, conversation):
        return self.agent.turn(context, conversation)

    def prepare(self, context, proposal, evidence):
        return self.saas.prepare(context, proposal, evidence)

    def execute(self, context, action):
        return self.saas.execute(context, action)


# shortcut: fixed demo login codes when SUPPORT_ACCOUNTS is unset; set real codes before exposing beyond localhost.
ACCOUNTS = json.loads(os.getenv("SUPPORT_ACCOUNTS", "{}")) or {
    "demo-a": {"tenant_id": "tenant_a", "actor_id": "owner_a", "role": "owner"},
    "demo-b": {"tenant_id": "tenant_b", "actor_id": "owner_b", "role": "owner"},
}
app = create_app(bridge=LocalBridge(), accounts=ACCOUNTS)
