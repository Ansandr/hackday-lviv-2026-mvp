import pytest
from src.support.models import CustomerTone
from src.support.triage import assess


def messages(*texts): return [{'role':'user','text':t} for t in texts]


@pytest.mark.parametrize('text,priority,emotion',[
    ('Хочу створити промокод','low','neutral'),
    ('З нас двічі списали гроші за підписку','high','neutral'),
    ('Це неприпустимо, мене це бісить','normal','angry'),
    ('Каса не працює, стоїть черга, клієнти чекають','urgent','neutral'),
    ('Каси не працюють у всіх закладах мережі','urgent','neutral'),
    ('Не розумію, як створити промокод','low','confused'),
    ('Боюся втратити гроші','normal','worried'),
    ('Знову не працює промокод, це набридло','normal','frustrated'),
    ('Дякую, все працює','low','positive'),
    ('Як створити промокод? Не терміново','low','neutral'),
])
def test_priority_and_tone(text,priority,emotion):
    a=assess(messages(text))
    assert a.priority==priority and a.customer_tone.emotion==emotion
    assert a.tone_source=='rules'


def test_short_clarification_keeps_impact_but_resolution_downgrades():
    assert assess(messages('З нас двічі списали гроші','business_01')).priority=='high'
    assert assess(messages('Каси не працюють у всіх закладах','Питання вирішено, вже працює')).priority=='low'


def test_model_emotion_never_overrides_priority_or_rules():
    tone=CustomerTone(emotion='angry',sentiment='negative',rationale='У тексті є обурення.')
    a=assess(messages('Хочу створити промокод'),tone)
    assert a.priority=='low' and a.customer_tone.emotion=='angry' and a.tone_source=='model'


def test_neutral_model_does_not_erase_explicit_confusion():
    tone=CustomerTone(emotion='neutral',sentiment='neutral',rationale='Спокійне питання.')
    a=assess(messages('Не розумію, як створити промокод'),tone)
    assert a.customer_tone.emotion=='confused' and a.tone_source=='rules'


def test_api_analysis_persists_sorts_and_survives_confirmation(tmp_path):
    from fastapi.testclient import TestClient
    from src.support.app import create_app
    from src.support.adapters import DemoBridge
    from src.support.store import Store
    client=TestClient(create_app(Store(str(tmp_path/'triage.db')),DemoBridge(),{'a':{'tenant_id':'a','actor_id':'a','role':'owner'}}))
    h={'Authorization':'Bearer '+client.post('/api/v1/session',json={'token':'a'}).json()['access_token']}
    ids=[]
    for text in ['Каса не працює, стоїть черга','Хочу створити промокод']:
        cid=client.post('/api/v1/conversations',headers=h,json={}).json()['conversation_id'];ids.append(cid)
        r=client.post(f'/api/v1/conversations/{cid}/messages',headers=h,json={'text':text,'client_message_id':'m'})
        assert r.status_code==200,r.text
        assert r.json()['analysis']['tone_source']=='rules'
        if r.json()['proposed_action']:
            aid=r.json()['proposed_action']['action_id']
            client.post(f'/api/v1/actions/{aid}/confirm',headers=h,json={'decision':'reject'})
            assert client.get('/api/v1/conversations/'+cid,headers=h).json()['latest_turn']['analysis']['priority']=='urgent'
    assert client.get('/api/v1/conversations?sort=priority',headers=h).json()[0]['conversation_id']==ids[0]
    assert client.get('/api/v1/conversations?sort=recent',headers=h).json()[0]['conversation_id']==ids[1]


def test_priority_survives_model_outage(tmp_path):
    from fastapi.testclient import TestClient
    from src.support.app import create_app
    from src.support.adapters import DemoBridge,ModelUnavailable
    from src.support.store import Store
    class Down(DemoBridge):
        def turn(self,*args): raise ModelUnavailable('down')
    c=TestClient(create_app(Store(str(tmp_path/'down.db')),Down(),{'a':{'tenant_id':'a','actor_id':'a','role':'owner'}}))
    h={'Authorization':'Bearer '+c.post('/api/v1/session',json={'token':'a'}).json()['access_token']}
    cid=c.post('/api/v1/conversations',headers=h,json={}).json()['conversation_id']
    assert c.post(f'/api/v1/conversations/{cid}/messages',headers=h,json={'text':'Каси не працюють у всіх закладах','client_message_id':'m'}).status_code==503
    assert c.get('/api/v1/conversations/'+cid,headers=h).json()['analysis']['priority']=='urgent'


def test_api_uses_model_tone_without_changing_priority(tmp_path):
    from fastapi.testclient import TestClient
    from src.support.app import create_app
    from src.support.adapters import DemoBridge
    from src.support.models import AgentResponse
    from src.support.store import Store
    class Emotional(DemoBridge):
        def turn(self,*args): return AgentResponse(reply='Уточніть параметри.',state='needs_input',customer_tone=CustomerTone(emotion='angry',sentiment='negative',rationale='Є обурення в тексті.'))
    c=TestClient(create_app(Store(str(tmp_path/'tone.db')),Emotional(),{'a':{'tenant_id':'a','actor_id':'a','role':'owner'}}))
    h={'Authorization':'Bearer '+c.post('/api/v1/session',json={'token':'a'}).json()['access_token']}
    cid=c.post('/api/v1/conversations',headers=h,json={}).json()['conversation_id']
    r=c.post(f'/api/v1/conversations/{cid}/messages',headers=h,json={'text':'Створити промокод','client_message_id':'m'}).json()
    assert r['analysis']['priority']=='low'
    assert r['analysis']['customer_tone']['emotion']=='angry' and r['analysis']['tone_source']=='model'
