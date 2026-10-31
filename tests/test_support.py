import concurrent.futures
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.support.adapters import DemoBridge, DependencyError, HttpBridge
from src.support.app import create_app
from src.support.models import AgentResponse, Execution
from src.support.store import Store


@pytest.fixture
def setup(tmp_path):
    bridge = DemoBridge()
    store = Store(str(tmp_path / 'support.db'))
    app = create_app(store, bridge, {
        'a': {'tenant_id': 'tenant_a', 'actor_id': 'owner_a', 'role': 'owner'},
        'b': {'tenant_id': 'tenant_b', 'actor_id': 'owner_b', 'role': 'owner'},
        'v': {'tenant_id': 'tenant_a', 'actor_id': 'viewer', 'role': 'viewer'},
    })
    client = TestClient(app)
    def auth(key):
        token = client.post('/api/v1/session', json={'token': key}).json()['access_token']
        return {'Authorization': 'Bearer ' + token}
    return client, store, bridge, auth


def start(client, headers, text='Промокод не працює'):
    cid = client.post('/api/v1/conversations', headers=headers, json={}).json()['conversation_id']
    r = client.post(f'/api/v1/conversations/{cid}/messages', headers=headers, json={'client_message_id': 'm1', 'text': text})
    assert r.status_code == 200, r.text
    return cid, r.json()


def test_session_and_isolation(setup):
    c, _, _, auth = setup
    assert c.get('/api/v1/conversations').status_code == 401
    a, b = auth('a'), auth('b')
    cid, turn = start(c, a)
    assert c.get('/api/v1/conversations/' + cid, headers=b).status_code == 404
    action = turn['proposed_action']['action_id']
    assert c.get('/api/v1/actions/' + action, headers=b).status_code == 404
    assert c.post('/api/v1/actions/' + action + '/confirm', headers=b, json={'decision': 'confirm'}).status_code == 404
    assert c.get('/api/v1/conversations', headers=b).json() == []


@pytest.mark.parametrize('text,kind', [('Промокод не працює','resync_pos'), ('Подвійне списання','cancel_duplicate_subscription'), ('Реквест на рефанд','create_refund_request')])
def test_actions_are_confirmed_and_idempotent(setup, text, kind):
    c, store, bridge, auth = setup
    a = auth('a')
    calls = []
    original = bridge.execute
    bridge.execute = lambda ctx, action: (calls.append(action['action_id']), original(ctx, action))[1]
    cid, turn = start(c, a, text)
    aid = turn['proposed_action']['action_id']
    assert turn['proposed_action']['type'] == kind
    assert not calls
    url = '/api/v1/actions/' + aid + '/confirm'
    first = c.post(url, headers=a, json={'decision': 'confirm'}).json()
    second = c.post(url, headers=a, json={'decision': 'confirm'}).json()
    assert first == second and len(calls) == 1
    assert first['status'] == 'succeeded'
    assert len(store.list('audit', 'tenant_a')) == 1
    if kind == 'create_refund_request':
        convo = c.get('/api/v1/conversations/' + cid, headers=a).json()
        assert convo['state'] == 'unresolved'
        assert 'Гроші ще не повернено' in convo['latest_turn']['reply']


def test_promo_questions_and_validation(setup):
    c, _, _, auth = setup
    a = auth('a')
    cid, turn = start(c, a, 'Хочу створити промокод')
    assert turn['state'] == 'needs_input' and turn['questions']
    import json
    params = {'venue_id': 'venue_01', 'discount_percent': 20, 'starts_at': '2026-10-31T12:00:00Z', 'expires_at': '2026-11-30T12:00:00Z', 'max_redemptions': 50}
    r = c.post(f'/api/v1/conversations/{cid}/messages', headers=a, json={'client_message_id': 'm2', 'text': json.dumps(params)})
    aid = r.json()['proposed_action']['action_id']
    result = c.post('/api/v1/actions/' + aid + '/confirm', headers=a, json={'decision': 'confirm'}).json()
    assert result['result']['after']['code'].startswith('DEMO-')


def test_reject_expiry_and_viewer(setup):
    c, store, _, auth = setup
    a = auth('a')
    _, turn = start(c, a)
    aid = turn['proposed_action']['action_id']
    url = '/api/v1/actions/' + aid + '/confirm'
    assert c.post(url, headers=auth('v'), json={'decision': 'confirm'}).status_code == 403
    assert c.post(url, headers=a, json={'decision': 'reject'}).json()['status'] == 'rejected'
    assert c.post(url, headers=a, json={'decision': 'confirm'}).json()['status'] == 'rejected'
    _, turn = start(c, a)
    aid = turn['proposed_action']['action_id']
    rec = store.get('action', aid, 'tenant_a')
    rec['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store.put('action', aid, 'tenant_a', rec)
    assert c.post('/api/v1/actions/' + aid + '/confirm', headers=a, json={'decision': 'confirm'}).json()['status'] == 'expired'


def test_message_retry_and_new_preview(setup):
    c, _, _, auth = setup
    a = auth('a')
    cid, first = start(c, a)
    url = f'/api/v1/conversations/{cid}/messages'
    assert c.post(url, headers=a, json={'client_message_id': 'm1', 'text': 'Промокод не працює'}).json() == first
    assert c.post(url, headers=a, json={'client_message_id': 'm1', 'text': 'other'}).status_code == 409
    c.post(url, headers=a, json={'client_message_id': 'm2', 'text': 'Подвійне списання'})
    assert c.get('/api/v1/actions/' + first['proposed_action']['action_id'], headers=a).json()['status'] == 'expired'


def test_upstream_failure_and_ambiguous_execution(setup):
    c, _, bridge, auth = setup
    a = auth('a')
    cid, turn = start(c, a)
    original = bridge.execute
    def fail(*args):
        raise DependencyError('timeout')
    bridge.execute = fail
    aid = turn['proposed_action']['action_id']
    url = '/api/v1/actions/' + aid + '/confirm'
    assert c.post(url, headers=a, json={'decision': 'confirm'}).status_code == 503
    assert c.get('/api/v1/actions/' + aid, headers=a).json()['status'] == 'executing'
    assert c.post(url, headers=a, json={'decision': 'reject'}).status_code == 409
    assert c.post(f'/api/v1/conversations/{cid}/messages', headers=a, json={'client_message_id': 'm2', 'text': 'new'}).status_code == 409
    bridge.execute = original
    assert c.post(url, headers=a, json={'decision': 'confirm'}).json()['status'] == 'succeeded'


def test_concurrent_confirmation(setup):
    c, _, bridge, auth = setup
    a = auth('a')
    _, turn = start(c, a)
    calls = []
    original = bridge.execute
    bridge.execute = lambda ctx, action: (calls.append(1), original(ctx, action))[1]
    url = '/api/v1/actions/' + turn['proposed_action']['action_id'] + '/confirm'
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: c.post(url, headers=a, json={'decision': 'confirm'}).json(), range(2)))
    assert results[0] == results[1] and len(calls) == 1


def test_unknown_actions_and_extra_identity_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AgentResponse.model_validate({'reply': 'x', 'state': 'unresolved', 'proposal': {'type': 'refund', 'parameters': {}}})
    with pytest.raises(ValidationError):
        AgentResponse.model_validate({'reply': 'x', 'state': 'unresolved', 'proposal': {'type': 'resync_pos', 'parameters': {'venue_id': 'v', 'tenant_id': 'other'}}})


def test_http_adapter_carries_server_context_and_idempotency(monkeypatch):
    import httpx
    from src.support.models import Context
    captured = []
    original = httpx.Client
    def handler(request):
        captured.append(request)
        return httpx.Response(200, json={'type':'resync_pos','resource_id':'v','before':{},'after':{},'verification':{'resolved':True}})
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    bridge = HttpBridge('http://agent', 'http://saas', 'service-key')
    bridge.execute(Context(tenant_id='tenant_a',actor_id='a',role='owner',request_id='r'), {'action_id':'act_1'})
    assert captured[0].headers['Idempotency-Key'] == 'act_1'
    assert captured[0].headers['Authorization'] == 'Bearer service-key'
    assert b'tenant_a' in captured[0].content


def test_persistence(tmp_path):
    path = str(tmp_path/'persist.db')
    store = Store(path)
    store.put('conversation','c','a',{'messages':[{'text':'hello'}]})
    assert Store(path).get('conversation','c','a')['messages'][0]['text'] == 'hello'


def test_ui_assets_and_no_inline_script(setup):
    c, _, _, _ = setup
    r = c.get('/')
    assert r.status_code == 200 and 'script-src' in r.headers['Content-Security-Policy']
    assert c.get('/assets/app.js').status_code == 200


def test_explicit_saas_rejection_is_terminal(setup):
    from src.support.adapters import ActionRejected
    c, _, bridge, auth = setup
    a = auth('a')
    _, turn = start(c, a)
    def reject(*args):
        raise ActionRejected('stale')
    bridge.execute = reject
    result = c.post('/api/v1/actions/' + turn['proposed_action']['action_id'] + '/confirm', headers=a, json={'decision':'confirm'}).json()
    assert result['status'] == 'failed' and result['error']['code'] == 'STALE_ACTION'


def test_remote_mode_never_falls_back_to_demo(tmp_path):
    c = TestClient(create_app(Store(str(tmp_path/'remote.db')), HttpBridge('', ''), {'a':{'tenant_id':'a','actor_id':'a','role':'owner'}}))
    token = c.post('/api/v1/session', json={'token':'a'}).json()['access_token']
    headers = {'Authorization':'Bearer '+token}
    cid = c.post('/api/v1/conversations', headers=headers, json={}).json()['conversation_id']
    assert c.post(f'/api/v1/conversations/{cid}/messages', headers=headers, json={'client_message_id':'m','text':'Промокод'}).status_code == 503
    assert c.get('/api/v1/conversations/'+cid, headers=headers).json()['messages'] == []


def test_remote_refund_verification_cannot_claim_money_returned(tmp_path):
    fixture = DemoBridge()
    class Bridge:
        turn = fixture.turn
        prepare = fixture.prepare
        def execute(self, ctx, action):
            return Execution(type='create_refund_request', resource_id='r',before=None,after={'status':'refunded'},verification={'resolved':True,'funds_moved':True})
    c = TestClient(create_app(Store(str(tmp_path/'bad.db')), Bridge(), {'a':{'tenant_id':'a','actor_id':'a','role':'owner'}}))
    a = {'Authorization':'Bearer '+c.post('/api/v1/session',json={'token':'a'}).json()['access_token']}
    _,turn = start(c,a,'Рефанд')
    assert c.post('/api/v1/actions/'+turn['proposed_action']['action_id']+'/confirm',headers=a,json={'decision':'confirm'}).status_code == 503


def test_model_outage_is_not_reported_as_saas_outage(setup):
    from src.support.adapters import ModelUnavailable
    c,_,bridge,auth=setup
    a=auth('a')
    cid=c.post('/api/v1/conversations',headers=a,json={}).json()['conversation_id']
    def unavailable(*args): raise ModelUnavailable('provider 503')
    bridge.turn=unavailable
    r=c.post(f'/api/v1/conversations/{cid}/messages',headers=a,json={'client_message_id':'m','text':'1 10\n2 заклад мій\nбезліміт використань'})
    assert r.status_code==503
    assert r.json()['error']['code']=='MODEL_UNAVAILABLE'
    assert 'SaaS' not in r.json()['error']['message']
