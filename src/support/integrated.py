from src.agent.runtime import Agent
from src.backend.product import Product, configured_state
from src.support.adapters import ActionRejected, DependencyError


class IntegratedBridge:
    mode = 'integrated'
    def __init__(self, product=None, agent=None):
        self.product=product or Product(configured_state())
        self.agent=agent or Agent(self.product)

    def turn(self, context, conversation):
        return self.call(self.agent.turn,context,conversation)

    def prepare(self, context, proposal, evidence):
        return self.call(self.product.prepare,context,proposal,evidence)

    def execute(self, context, action):
        return self.call(self.product.execute,context,action)

    @staticmethod
    def call(fn,*args):
        try:
            return fn(*args)
        except (ActionRejected,DependencyError):
            raise
        except Exception as exc:
            raise DependencyError('Product or agent dependency unavailable') from exc
