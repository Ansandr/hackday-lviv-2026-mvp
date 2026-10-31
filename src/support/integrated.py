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

    def escalation_context(self,context,evidence_ids,actions):
        state=self.product.read(context)
        logs=[log for log in state['logs'] if log['log_id'] in set(evidence_ids)]
        venues={a['parameters'].get('venue_id') for a in actions}
        businesses={a['parameters'].get('business_id') for a in actions}
        for log in logs:
            venues.add(log['safe_details'].get('venue_id'))
            businesses.add(log['safe_details'].get('business_id'))
        facts={'pos_state':{v:s for v,s in state['pos_state'].items() if v in venues},'checkouts':[c for c in state['checkouts'].values() if c['venue_id'] in venues],'subscriptions':[s for s in state['subscriptions'].values() if s['business_id'] in businesses],'payments':[p for p in state['payments'].values() if p['business_id'] in businesses]}
        knowledge=[]
        from pathlib import Path
        for path in (Path(__file__).resolve().parents[2]/'data/docs').glob('*.md'):
            if 'FILE-'+path.stem in evidence_ids:knowledge.append({'kb_id':'FILE-'+path.stem,'text':path.read_text(encoding='utf-8')[:6000]})
        if hasattr(self.product.state,'collection'):
            database=self.product.state.collection.database
            for collection,filters in [('kb_global',{}),('kb_tenant',{'tenant_id':context.tenant_id})]:
                for doc in database[collection].find({**filters,'kb_id':{'$in':evidence_ids},'status':'approved'},{'_id':0,'kb_id':1,'title':1,'text':1}).limit(10):knowledge.append(doc)
        return {'logs':logs,'facts':facts,'knowledge':knowledge,'context_status':'collected'}

    @staticmethod
    def call(fn,*args):
        try:
            return fn(*args)
        except (ActionRejected,DependencyError):
            raise
        except Exception as exc:
            raise DependencyError('Product or agent dependency unavailable') from exc
