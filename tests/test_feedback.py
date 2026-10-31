import pytest
from fastapi.testclient import TestClient

from src.agent.runtime import Agent
from src.backend.product import LocalState,Product
from src.support.app import create_app
from src.support.integrated import IntegratedBridge
from src.support.store import Store
from src.support.tickets import DeliveryRejected,DeliveryUnknown,redact


class Sender:
    def __init__(self):self.calls=[];self.failures={};self.chats=['one','two']
    def targets(self):return self.chats
    def send(self,chat,ticket):
        self.calls.append((chat,ticket['ticket_id']))
        if chat in self.failures:raise self.failures[chat]()
        return 'message_'+chat


@pytest.fixture
def setup(tmp_path):
    state=LocalState(str(tmp_path/'p.db'));state.initialize('tenant_a');state.initialize('tenant_b')
    product=Product(state)
    steps=iter([
        {'tool':'get_trace','arguments':{'trace_id':'trace_checkout_01'}},
        {'reply':'Підтвердіть синхронізацію.','state':'unresolved','proposal':{'type':'resync_pos','parameters':{'venue_id':'venue_01'}}},
    ])
    agent=Agent(product,model=lambda *args:next(steps))
    sender=Sender();store=Store(str(tmp_path/'s.db'))
    app=create_app(store,IntegratedBridge(product,agent),{'a':{'tenant_id':'tenant_a','actor_id':'a','role':'owner'},'b':{'tenant_id':'tenant_b','actor_id':'b','role':'owner'}},notifier=sender)
    c=TestClient(app)
    def auth(key):return {'Authorization':'Bearer '+c.post('/api/v1/session',json={'token':key}).json()['access_token']}
    h=auth('a');cid=c.post('/api/v1/conversations',headers=h,json={}).json()['conversation_id']
    r=c.post(f'/api/v1/conversations/{cid}/messages',headers=h,json={'client_message_id':'m','text':'Каса не працює, стоїть черга. Це набридло.'})
    assert r.status_code==200,r.text
    assert r.json()['resolution_prompt'] is None
    aid=r.json()['proposed_action']['action_id']
    c.post(f'/api/v1/actions/{aid}/confirm',headers=h,json={'decision':'confirm'})
    prompt=c.get('/api/v1/conversations/'+cid,headers=h).json()['latest_turn']['resolution_prompt']
    return c,h,cid,prompt,sender,store,auth,agent


def submit(setup,resolved=False,comment='Промокод усе ще не застосовується'):
    c,h,cid,prompt,*_=setup
    return c.post(f'/api/v1/conversations/{cid}/feedback',headers=h,json={'prompt_id':prompt['prompt_id'],'resolved':resolved,'comment':comment})


def test_positive_feedback_closes_without_ticket(setup):
    c,h,cid,_,sender,store,*_=setup
    r=submit(setup,True,'Дякую, працює')
    assert r.status_code==200 and r.json()['state']=='resolved' and r.json()['ticket'] is None
    assert not sender.calls and not store.list('ticket','tenant_a')
    assert c.get('/api/v1/conversations/'+cid,headers=h).json()['resolution_prompt'] is None


def test_unresolved_ticket_contains_context_and_delivers_once(setup):
    c,h,cid,_,sender,store,auth,_=setup
    r=submit(setup);assert r.status_code==200,r.text
    ticket=r.json()['ticket'];tid=ticket['ticket_id']
    assert ticket['delivery']['status']=='sent' and ticket['delivery']['delivered']==2
    assert len(sender.calls)==2
    assert submit(setup).json()==r.json() and len(sender.calls)==2
    report=c.get('/api/v1/tickets/'+tid,headers=h).json()
    assert len(report['diagnostics']['logs'])==3
    assert report['actions'][0]['type']=='resync_pos'
    assert report['analysis']['priority']=='urgent'
    assert report['analysis']['customer_tone']['emotion']=='frustrated'
    assert report['original_request'].startswith('Каса')
    assert 'targets' not in report['delivery']
    assert c.get('/api/v1/tickets/'+tid,headers=auth('b')).status_code==404
    assert c.post('/api/v1/tickets/'+tid+'/delivery',headers=auth('b')).status_code==404
    assert c.post('/api/v1/tickets/'+tid+'/delivery',headers=h).json()['delivery']['status']=='sent'
    assert len(sender.calls)==2
    assert submit(setup,True).status_code==409


def test_partial_delivery_retries_only_failed_recipient(setup):
    c,h,_,_,sender,*_=setup
    sender.failures['two']=DeliveryRejected
    ticket=submit(setup).json()['ticket']
    assert ticket['delivery']['status']=='partial'
    sender.failures.clear()
    r=c.post('/api/v1/tickets/'+ticket['ticket_id']+'/delivery',headers=h).json()
    assert r['delivery']['status']=='sent'
    assert [chat for chat,_ in sender.calls]==['one','two','two']


def test_uncertain_delivery_is_not_blindly_repeated(setup):
    c,h,_,_,sender,*_=setup
    sender.failures['two']=DeliveryUnknown
    ticket=submit(setup).json()['ticket']
    assert ticket['delivery']['uncertain'] is True
    c.post('/api/v1/tickets/'+ticket['ticket_id']+'/delivery',headers=h)
    assert len(sender.calls)==2


def test_ticket_persists_without_telegram_destination(setup):
    c,h,_,_,sender,store,*_=setup
    sender.chats=[]
    ticket=submit(setup).json()['ticket']
    assert ticket['delivery']['status']=='pending'
    assert store.get('ticket',ticket['ticket_id'],'tenant_a')
    sender.chats=['one','two']
    assert c.post('/api/v1/tickets/'+ticket['ticket_id']+'/delivery',headers=h).json()['delivery']['status']=='sent'


def test_old_resolution_question_cannot_create_ticket(setup):
    c,h,cid,prompt,sender,_,_,agent=setup
    agent.model=lambda *args:{'reply':'Уточніть ситуацію.','state':'needs_input','questions':[{'field':'details','prompt':'Що сталося?'}]}
    c.post(f'/api/v1/conversations/{cid}/messages',headers=h,json={'client_message_id':'next','text':'Інше запитання'})
    assert submit(setup).status_code==409 and not sender.calls


def test_ticket_redacts_credentials_and_pii():
    text='123456789:abcdefghijklmnopqrstuvwxyzABCDE owner@cafe.ua 4111 1111 1111 1111'
    safe=redact({'text':text,'api_key':'abc','safe_details':{'password':'p'}})
    assert 'abcdefghijklmnopqrstuvwxyz' not in safe['text'] and 'owner@' not in safe['text'] and '4111' not in safe['text']
    assert safe['api_key']=='[REDACTED]' and safe['safe_details']['password']=='[REDACTED]'


def test_typed_no_creates_ticket_without_another_model_call(setup):
    c,h,cid,_,sender,*_=setup
    body={'client_message_id':'typed-no','text':'Ні, код досі не працює'}
    r=c.post(f'/api/v1/conversations/{cid}/messages',headers=h,json=body)
    assert r.status_code==200,r.text
    assert r.json()['support_ticket']['ticket_id']
    assert len(sender.calls)==2
    assert c.post(f'/api/v1/conversations/{cid}/messages',headers=h,json=body).json()==r.json()
    assert len(sender.calls)==2


def test_pending_refund_is_not_marked_financially_resolved(setup):
    c,h,cid,prompt,_,store,*_=setup
    store.put('action','refund-fake','tenant_a',{'action_id':'refund-fake','conversation_id':cid,'type':'create_refund_request','status':'succeeded'})
    r=submit(setup,True,'Дякую за подання запиту')
    assert r.json()['state']=='unresolved'
    last=c.get('/api/v1/conversations/'+cid,headers=h).json()['latest_turn']
    assert 'гроші поки не повернено' in last['reply']
