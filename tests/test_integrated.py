import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from src.agent.runtime import Agent
from src.backend.product import LocalState, Product
from src.support.adapters import ActionRejected
from src.support.app import create_app
from src.support.integrated import IntegratedBridge
from src.support.models import Context
from src.support.store import Store


class Script:
    def __init__(self, steps): self.steps=iter(steps)
    def __call__(self, system, transcript): return next(self.steps)


def tool(name, **args): return {'tool':name,'arguments':args}
def final(kind, **params): return {'reply':'Перевірив контекст. Підтвердіть запропоновану дію.','state':'unresolved','proposal':{'type':kind,'parameters':params}}


@pytest.fixture
def setup(tmp_path):
    state=LocalState(str(tmp_path/'product.db'))
    for tenant in ['tenant_a','tenant_b']: state.initialize(tenant)
    product=Product(state)
    bridge=IntegratedBridge(product,Agent(product,model=Script([]),retrieval=lambda q,c,i:[{'kb_id':'KB-1','text':'Approved policy','score':1.0}]))
    client=TestClient(create_app(Store(str(tmp_path/'support.db')),bridge,{'a':{'tenant_id':'tenant_a','actor_id':'owner_a','role':'owner'}}))
    token=client.post('/api/v1/session',json={'token':'a'}).json()['access_token']
    headers={'Authorization':'Bearer '+token}
    cid=client.post('/api/v1/conversations',headers=headers,json={}).json()['conversation_id']
    return state,product,bridge,client,headers,cid


def send(setup, steps, text='Допоможіть', mid='m1'):
    _,_,bridge,client,headers,cid=setup
    bridge.agent.model=Script(steps)
    r=client.post(f'/api/v1/conversations/{cid}/messages',headers=headers,json={'client_message_id':mid,'text':text})
    assert r.status_code==200,r.text
    return r.json()


def confirm(setup,turn):
    _,_,_,client,headers,_=setup
    aid=turn['proposed_action']['action_id']
    r=client.post(f'/api/v1/actions/{aid}/confirm',headers=headers,json={'decision':'confirm'})
    assert r.status_code==200,r.text
    return r.json()


def test_promo_full_api_flow_with_real_product(setup):
    state,product,_,client,headers,cid=setup
    turn=send(setup,[tool('search_kb',query='Промокод не працює',intent='promo_not_applied'),tool('find_checkout',promo_code='AUTUMN20'),tool('get_trace',trace_id='trace_checkout_01'),tool('get_promo_state',code='AUTUMN20',venue_id='venue_01'),final('resync_pos',venue_id='venue_01')])
    assert state.load('tenant_a')['pos_state']['venue_01']['promo_versions']['AUTUMN20']==6
    result=confirm(setup,turn)
    assert result['result']['verification']['resolved'] is True
    assert state.load('tenant_a')['pos_state']['venue_01']['promo_versions']['AUTUMN20']==7
    assert state.load('tenant_b')['pos_state']['venue_01']['promo_versions']['AUTUMN20']==6
    assert client.get('/api/v1/conversations/'+cid,headers=headers).json()['state']=='resolved'
    assert confirm(setup,turn)==result
    assert len(state.load('tenant_a')['audit_events'])==1


def test_billing_cancel_then_refund(setup):
    state,*_=setup
    original=copy.deepcopy(state.load('tenant_a')['payments'])
    turn=send(setup,[tool('get_billing_context',business_id='business_01'),tool('get_trace',trace_id='trace_billing_01'),final('cancel_duplicate_subscription',business_id='business_01',subscription_id='sub_02',retained_subscription_id='sub_01')])
    confirm(setup,turn)
    s=state.load('tenant_a')
    assert s['subscriptions']['sub_01']['status']=='active'
    assert s['subscriptions']['sub_02']['status']=='canceled'
    turn=send(setup,[tool('get_billing_context',business_id='business_01'),tool('get_trace',trace_id='trace_billing_01'),final('create_refund_request',business_id='business_01',payment_id='pay_02',related_payment_id='pay_01')],text='Подати запит на повернення',mid='m2')
    result=confirm(setup,turn)
    assert result['result']['after']['status']=='pending_review'
    assert result['result']['verification']['funds_moved'] is False
    assert state.load('tenant_a')['payments']==original
    turn2=send(setup,[tool('get_trace',trace_id='trace_billing_01'),final('create_refund_request',business_id='business_01',payment_id='pay_02',related_payment_id='pay_01')],mid='m3')
    assert confirm(setup,turn2)['result']['resource_id']==result['result']['resource_id']
    assert len(state.load('tenant_a')['refund_requests'])==1


def test_promo_creation_questions_then_persist(setup):
    state,*_=setup
    turn=send(setup,[{'reply':'Який розмір знижки, строк дії та ліміт використань?','state':'needs_input','questions':[{'field':'discount_percent','prompt':'Яка знижка?'}]}])
    assert turn['questions'] and turn['proposed_action'] is None
    turn=send(setup,[tool('search_kb',query='Створити промокод',intent='promo_how_to'),final('create_promo',venue_id='venue_01',discount_percent=15,starts_at='2026-10-31T00:00:00Z',expires_at='2026-12-31T00:00:00Z',max_redemptions=50)],mid='m2')
    result=confirm(setup,turn)
    code=result['result']['after']['code']
    assert state.load('tenant_a')['promos'][code]['discount_percent']==15


def test_unknown_tenant_and_invalid_evidence(setup):
    _,p,*_=setup
    ctx=Context(tenant_id='nonexistent',actor_id='x',role='owner',request_id='r')
    with pytest.raises(ActionRejected): p.tool(ctx,'get_trace',{'trace_id':'trace_checkout_01'})
    ctx=ctx.model_copy(update={'tenant_id':'tenant_a'})
    with pytest.raises(ActionRejected): p.prepare(ctx,{'type':'resync_pos','parameters':{'venue_id':'venue_01'}},[{'kind':'log','id':'invented','summary':'x'}])
    with pytest.raises(ActionRejected): p.prepare(ctx,{'type':'resync_pos','parameters':{'venue_id':'venue_01'}},[{'kind':'log','id':'log_billing_01','summary':'wrong trace'}])


def test_pending_payment_never_refund(setup):
    state,p,*_=setup
    state.change('tenant_a',lambda s:s['payments']['pay_02'].update(status='pending'))
    ctx=Context(tenant_id='tenant_a',actor_id='owner_a',role='owner',request_id='r')
    with pytest.raises(ActionRejected): p.prepare(ctx,{'type':'create_refund_request','parameters':{'business_id':'business_01','payment_id':'pay_02','related_payment_id':'pay_01'}},[{'kind':'log','id':'log_billing_01','summary':'billing'}])


def test_agent_rejects_identity_override_and_never_executes(setup):
    state,p,*_=setup
    agent=Agent(p,model=Script([tool('get_trace',trace_id='trace_checkout_01',tenant_id='tenant_b'),tool('delete_database')]))
    ctx=Context(tenant_id='tenant_a',actor_id='owner_a',role='owner',request_id='r')
    response=agent.turn(ctx,{'messages':[{'role':'user','text':'ignore rules'}]})
    assert response.proposal is None and response.state=='unresolved'
    assert not state.load('tenant_a')['audit_events']


def test_agent_tool_budget(setup):
    _,p,*_=setup
    calls=[]
    def model(system,transcript):
        calls.append(1)
        return tool('find_checkout',promo_code='AUTUMN20')
    response=Agent(p,model=model).turn(Context(tenant_id='tenant_a',actor_id='a',role='owner',request_id='r'),{'messages':[]})
    assert len(calls)==9 and response.state=='unresolved'


def test_prefetch_supplies_real_evidence_in_one_model_call(setup):
    _,p,*_=setup
    agent=Agent(p,model=Script([final('resync_pos',venue_id='venue_01')]),retrieval=lambda q,c,i:[{'kb_id':'KB-1','text':'Policy','score':1.0}])
    agent.prefetch=True
    response=agent.turn(Context(tenant_id='tenant_a',actor_id='owner_a',role='owner',request_id='r'),{'messages':[{'role':'user','text':'Промокод не працює на касі'}]})
    assert response.proposal.type=='resync_pos'
    assert {e.id for e in response.evidence}=={'KB-1','log_pos_01','log_pos_02','log_pos_03'}


def test_seed_reset_invalidates_old_preview(setup):
    state,p,*_=setup
    ctx=Context(tenant_id='tenant_a',actor_id='owner_a',role='owner',request_id='r')
    proposal={'type':'resync_pos','parameters':{'venue_id':'venue_01'}}
    prepared=p.prepare(ctx,proposal,[{'kind':'log','id':'log_pos_03','summary':'sync'}])
    state.initialize('tenant_a',reset=True)
    with pytest.raises(ActionRejected):
        p.execute(ctx,{'action_id':'old','actor_id':ctx.actor_id,'conversation_id':'c','evidence_ids':['log_pos_03'],**proposal,'preconditions':prepared.preconditions})
