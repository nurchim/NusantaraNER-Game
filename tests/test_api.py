from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert body['adventure_2d'] is True


def test_predict():
    r = client.post('/api/predict', json={'text': 'Rumah Gadang berasal dari Sumatera Barat.'})
    assert r.status_code == 200
    assert 'entities' in r.json()


def test_game_catalog():
    r = client.get('/api/game/catalog')
    assert r.status_code == 200
    body = r.json()
    assert body['count'] >= 8
    assert body['items'][0]['name']


def test_game_session():
    r = client.post('/api/game/session', json={'mode': 'mixed', 'count': 4, 'seed': 42})
    assert r.status_code == 200
    body = r.json()
    assert body['count'] >= 1
    assert body['questions']
    assert all('answer' in q and 'options' in q for q in body['questions'])


def test_adventure_map():
    r = client.get('/api/game/adventure-map')
    assert r.status_code == 200
    body = r.json()
    assert body['node_count'] >= 8
    assert all(0 <= n['x'] <= 1 and 0 <= n['y'] <= 1 for n in body['nodes'])


def test_adventure_challenge():
    m = client.get('/api/game/adventure-map').json()
    gid = m['nodes'][0]['id']
    r = client.post(f'/api/game/adventure/{gid}', json={'count': 3, 'seed': 42})
    assert r.status_code == 200
    body = r.json()
    assert body['game']['id'] == gid
    assert body['questions']
    assert all('answer' in q and 'options' in q for q in body['questions'])


def test_custom_game():
    r = client.post('/api/game/custom', json={'text': 'Tari Saman berkembang dalam masyarakat Gayo di Aceh.'})
    assert r.status_code == 200
    body = r.json()
    assert 'entities' in body and 'questions' in body


def test_pages():
    home = client.get('/')
    assert home.status_code == 200
    assert 'adventureCanvas' in home.text
    assert client.get('/game').status_code == 200
    assert client.get('/classic').status_code == 200
    assert client.get('/ner').status_code == 200


def test_2d_static_assets():
    css = client.get('/web/adventure2d.css')
    js = client.get('/web/adventure2d.js')
    assert css.status_code == 200
    assert 'text/css' in css.headers.get('content-type', '')
    assert js.status_code == 200
    assert 'javascript' in js.headers.get('content-type', '')
    assert 'Festival Permainan Nusantara' in js.text or 'adventureCanvas' in client.get('/').text
