from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


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


def test_custom_game():
    r = client.post('/api/game/custom', json={'text': 'Tari Saman berkembang dalam masyarakat Gayo di Aceh.'})
    assert r.status_code == 200
    body = r.json()
    assert 'entities' in body and 'questions' in body


def test_pages():
    assert client.get('/').status_code == 200
    assert client.get('/game').status_code == 200
    assert client.get('/ner').status_code == 200
