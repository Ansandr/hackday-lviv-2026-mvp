import copy
import json
import os
import secrets
from datetime import datetime, timezone

from pydantic import TypeAdapter

from src.support.adapters import ActionRejected, DependencyError
from src.support.models import Execution, Prepared, Proposal
from src.support.store import Store


def utc():
    return datetime.now(timezone.utc).isoformat()


def seed_state(tenant):
    return {
        'tenant_id': tenant, 'version': 1,
        'venues': {'venue_01': {'business_id': 'business_01', 'timezone': 'Europe/Kyiv'}},
        'promos': {'AUTUMN20': {'promo_id':'promo_01','code':'AUTUMN20','venue_id':'venue_01','discount_percent':20,'starts_at':'2026-01-01T00:00:00Z','expires_at':'2027-01-01T00:00:00Z','max_redemptions':100,'redemption_count':0,'status':'active','version':7}},
        'pos_state': {'venue_01': {'promo_versions': {'AUTUMN20': 6}}},
        'checkouts': {'checkout_01': {'checkout_id':'checkout_01','business_id':'business_01','venue_id':'venue_01','promo_code':'AUTUMN20','trace_id':'trace_checkout_01'}},
        'subscriptions': {sid:{'subscription_id':sid,'business_id':'business_01','plan_id':'pro','period_start':'2026-10-01T00:00:00Z','period_end':'2026-11-01T00:00:00Z','status':'active','renewal_enabled':True} for sid in ['sub_01','sub_02']},
        'payments': {pid:{'payment_id':pid,'subscription_id':sid,'business_id':'business_01','amount_minor':99000,'currency':'UAH','status':'captured','trace_id':'trace_billing_01'} for pid,sid in [('pay_01','sub_01'),('pay_02','sub_02')]},
        'logs': [
            {'log_id':'log_pos_01','trace_id':'trace_checkout_01','parent_event_id':None,'event':'PROMO_CACHE_MISS','service':'pos','occurred_at':'2026-10-31T12:00:00Z','safe_details':{'checkout_id':'checkout_01','venue_id':'venue_01','actual_version':6}},
            {'log_id':'log_pos_02','trace_id':'trace_checkout_01','parent_event_id':'log_pos_01','event':'PROMO_LOOKUP_OK','service':'promo','occurred_at':'2026-10-31T12:00:01Z','safe_details':{'code':'AUTUMN20','version':7}},
            {'log_id':'log_pos_03','trace_id':'trace_checkout_01','parent_event_id':'log_pos_02','event':'POS_SYNC_FAILED','service':'sync','occurred_at':'2026-10-31T12:00:02Z','safe_details':{'reason':'delivery_timeout','venue_id':'venue_01'}},
            {'log_id':'log_billing_01','trace_id':'trace_billing_01','parent_event_id':None,'event':'SUBSCRIPTION_CREATE_RETRY','service':'billing','occurred_at':'2026-10-01T12:00:00Z','safe_details':{'business_id':'business_01','subscriptions':['sub_01','sub_02'],'reason':'missing_idempotency_key'}}],
        'refund_requests': {}, 'executions': {}, 'audit_events': []}


class LocalState:
    def __init__(self, path):
        self.store = Store(path)

    def load(self, tenant):
        return self.store.get('product', tenant, tenant)

    def initialize(self, tenant, reset=False):
        with self.store.lock:
            current=self.load(tenant)
            if reset or current is None:
                fresh=seed_state(tenant)
                if current: fresh['version']=current['version']+1
                self.store.put('product', tenant, tenant, fresh)

    def change(self, tenant, fn):
        with self.store.lock:
            state = self.load(tenant)
            if state is None:
                raise ActionRejected('Tenant not seeded')
            result = fn(state)
            state['version'] += 1
            self.store.put('product', tenant, tenant, state)
            return result


class MongoState:
    """One bounded demo aggregate per tenant: mutation/result/audit commit in one CAS write."""
    def __init__(self, uri, database):
        from pymongo import MongoClient
        self.client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        self.collection = self.client[database]['mock_tenant_state']

    def load(self, tenant):
        state = self.collection.find_one({'_id':tenant,'tenant_id':tenant})
        if state:
            state.pop('_id', None)
        return state

    def initialize(self, tenant, reset=False):
        if reset:
            current=self.load(tenant)
            fresh=seed_state(tenant)
            if current: fresh['version']=current['version']+1
            self.collection.replace_one({'_id':tenant}, {'_id':tenant,**fresh},upsert=True)
        else:
            self.collection.update_one({'_id':tenant},{'$setOnInsert':seed_state(tenant)},upsert=True)

    def change(self, tenant, fn):
        for _ in range(5):
            state = self.load(tenant)
            if not state:
                raise ActionRejected('Tenant not seeded')
            version = state['version']
            result = fn(state)
            state['version'] = version + 1
            if self.collection.replace_one({'_id':tenant,'tenant_id':tenant,'version':version},{'_id':tenant,**state}).modified_count:
                return result
        raise DependencyError('Concurrent product update; retry same action ID')


def configured_state():
    if os.getenv('SUPPORT_PRODUCT_STORE', 'mongo') == 'sqlite':
        return LocalState(os.getenv('SUPPORT_PRODUCT_DB', 'product.sqlite3'))
    if not os.getenv('MONGODB_URI'):
        raise DependencyError('Set MONGODB_URI or explicitly choose SUPPORT_PRODUCT_STORE=sqlite')
    return MongoState(os.environ['MONGODB_URI'], os.getenv('MONGODB_DB','support'))


class Product:
    def __init__(self, state):
        self.state = state

    def read(self, ctx):
        state = self.state.load(ctx.tenant_id)
        if not state:
            raise ActionRejected('Tenant not seeded')
        return state

    def tool(self, ctx, name, args):
        s = self.read(ctx)
        if name == 'get_catalog':
            return {'venues':s['venues'],'business_ids':list({v['business_id'] for v in s['venues'].values()})}
        if name == 'find_checkout':
            return [v for v in s['checkouts'].values() if all(v.get(k)==value for k,value in args.items())]
        if name == 'get_trace':
            return [x for x in s['logs'] if x['trace_id']==args['trace_id']][:30]
        if name == 'get_promo_state':
            p = s['promos'].get(args['code'])
            if not p or p['venue_id'] != args['venue_id']:
                raise ActionRejected('Promo not found')
            return {**p,'pos_version':s['pos_state'][args['venue_id']]['promo_versions'].get(args['code'])}
        if name == 'get_billing_context':
            b = args['business_id']
            return {'subscriptions':[v for v in s['subscriptions'].values() if v['business_id']==b], 'payments':[v for v in s['payments'].values() if v['business_id']==b], 'trace_ids':list({v['trace_id'] for v in s['payments'].values() if v['business_id']==b})}
        if name == 'validate_checkout':
            return self.checkout(s,args['checkout_id'])
        raise ActionRejected('Unknown read tool')

    @staticmethod
    def checkout(s, cid):
        c = s['checkouts'].get(cid)
        if not c:
            raise ActionRejected('Checkout not found')
        p = s['promos'].get(c['promo_code'])
        accepted = bool(p and p['status']=='active' and p['venue_id']==c['venue_id'] and datetime.fromisoformat(p['starts_at'])<=datetime.now(timezone.utc)<datetime.fromisoformat(p['expires_at']) and p['redemption_count']<p['max_redemptions'] and s['pos_state'][c['venue_id']]['promo_versions'].get(c['promo_code'])==p['version'])
        return {'accepted':accepted,'rejection_code':None if accepted else 'PROMO_NOT_APPLICABLE','checkout_id':cid}

    @staticmethod
    def duplicate(s, a, b, business):
        if a == b:
            raise ActionRejected('Distinct captured payments required')
        x,y = s['payments'].get(a),s['payments'].get(b)
        if not x or not y or any(p['business_id']!=business or p['status']!='captured' for p in [x,y]) or (x['amount_minor'],x['currency'])!=(y['amount_minor'],y['currency']):
            raise ActionRejected('Not a duplicate captured charge')
        sx,sy = s['subscriptions'][x['subscription_id']],s['subscriptions'][y['subscription_id']]
        if sx['plan_id']!=sy['plan_id'] or max(sx['period_start'],sy['period_start'])>=min(sx['period_end'],sy['period_end']):
            raise ActionRejected('Different service periods or plans')
        return x,y

    def validate(self, s, proposal):
        p = TypeAdapter(Proposal).validate_python(proposal).model_dump(mode='json')
        kind,a = p['type'],p['parameters']
        if kind in ('resync_pos','create_promo') and a['venue_id'] not in s['venues']:
            raise ActionRejected('Venue not found')
        if kind == 'create_refund_request':
            self.duplicate(s,a['payment_id'],a['related_payment_id'],a['business_id'])
        if kind == 'cancel_duplicate_subscription':
            x,y = s['subscriptions'].get(a['subscription_id']),s['subscriptions'].get(a['retained_subscription_id'])
            if not x or not y or x==y or x['status']!='active' or y['status']!='active' or x['business_id']!=a['business_id'] or y['business_id']!=a['business_id']:
                raise ActionRejected('Active duplicate subscriptions required')
            payments = [p for p in s['payments'].values() if p['subscription_id']==a['subscription_id']]
            retained = [p for p in s['payments'].values() if p['subscription_id']==a['retained_subscription_id']]
            if not payments or not retained:
                raise ActionRejected('Payment evidence missing')
            self.duplicate(s,payments[0]['payment_id'],retained[0]['payment_id'],a['business_id'])
        return p

    def prepare(self, ctx, proposal, evidence):
        s = self.read(ctx)
        p = self.validate(s,proposal)
        # Operational evidence must come from this tenant's actual logs.
        valid = {x['log_id'] for x in s['logs']}
        if any(e['kind']=='log' and e['id'] not in valid for e in evidence):
            raise ActionRejected('Unknown operational evidence')
        if p['type'] != 'create_promo' and not any(e['kind']=='log' for e in evidence):
            raise ActionRejected('Read correlated logs before proposing correction')
        selected={e['id'] for e in evidence if e['kind']=='log'}
        logs=[x for x in s['logs'] if x['log_id'] in selected]
        a=p['parameters']
        if p['type']=='resync_pos':
            if not any(x['event']=='POS_SYNC_FAILED' and x['safe_details'].get('venue_id')==a['venue_id'] for x in logs):
                raise ActionRejected('Missing sync failure for this venue')
        if p['type'] in ('cancel_duplicate_subscription','create_refund_request'):
            traces={pay['trace_id'] for pay in s['payments'].values() if pay['business_id']==a['business_id']}
            if not any(x['trace_id'] in traces and x['safe_details'].get('business_id')==a['business_id'] for x in logs):
                raise ActionRejected('Missing billing trace for this business')
        preview = {}
        if p['type']=='create_refund_request':
            pay = s['payments'][p['parameters']['payment_id']]
            preview = {k:pay[k] for k in ('amount_minor','currency')}
        labels={'resync_pos':'Синхронізувати касу','create_promo':'Створити промокод','cancel_duplicate_subscription':'Скасувати зайву підписку','create_refund_request':'Зареєструвати запит на повернення коштів'}
        return Prepared(summary=labels[p['type']],preconditions={'version':s['version']},preview=preview,evidence_ids=[e['id'] for e in evidence])

    def execute(self, ctx, action):
        if ctx.role!='owner' or ctx.actor_id!=action['actor_id']:
            raise ActionRejected('Owner confirmation required')
        def mutate(s):
            aid=action['action_id']
            if aid in s['executions']:
                return s['executions'][aid]
            if action['preconditions']['version']!=s['version']:
                raise ActionRejected('Stale product version')
            p = self.validate(s,{'type':action['type'],'parameters':action['parameters']})
            kind,a = p['type'],p['parameters']
            before=None; verification={'persisted':True,'funds_moved':False}
            if kind=='resync_pos':
                venue=a['venue_id'];before=copy.deepcopy(s['pos_state'][venue])
                s['pos_state'][venue]={'promo_versions':{code:p['version'] for code,p in s['promos'].items() if p['venue_id']==venue},'last_sync_at':utc()}
                after=s['pos_state'][venue];rid=venue
                checks=[self.checkout(s,c['checkout_id']) for c in s['checkouts'].values() if c['venue_id']==venue]
                verification.update({'checkouts':checks,'resolved':bool(checks) and all(c['accepted'] for c in checks)})
            elif kind=='cancel_duplicate_subscription':
                rid=a['subscription_id'];before=copy.deepcopy(s['subscriptions'][rid])
                s['subscriptions'][rid].update(status='canceled',renewal_enabled=False)
                after=s['subscriptions'][rid]
                verification['retained_active']=s['subscriptions'][a['retained_subscription_id']]['status']=='active'
            elif kind=='create_promo':
                code='VENUE-'+secrets.token_hex(4).upper()
                while code in s['promos']: code='VENUE-'+secrets.token_hex(4).upper()
                rid='promo_'+secrets.token_hex(8)
                after={'promo_id':rid,'code':code,**a,'redemption_count':0,'status':'active','version':1}
                s['promos'][code]=after;verification['resolved']=True
            else:
                pay=s['payments'][a['payment_id']]
                existing=s['refund_requests'].get(a['payment_id'])
                before=copy.deepcopy(existing)
                after=existing or {'refund_request_id':'refund_'+secrets.token_hex(8),**a,'amount_minor':pay['amount_minor'],'currency':pay['currency'],'status':'pending_review','reason':'suspected_duplicate_charge','actor_id':ctx.actor_id,'conversation_id':action['conversation_id'],'action_id':aid,'evidence_ids':action['evidence_ids'],'created_at':utc()}
                s['refund_requests'][a['payment_id']]=after;rid=after['refund_request_id']
            result=Execution(type=kind,resource_id=rid,before=before,after=copy.deepcopy(after),verification=verification).model_dump(mode='json')
            s['executions'][aid]=result
            s['audit_events'].append({'action_id':aid,'actor_id':ctx.actor_id,'type':kind,'occurred_at':utc(),'result':copy.deepcopy(result)})
            return result
        return Execution.model_validate(self.state.change(ctx.tenant_id,mutate))
