
def test_app(client):
    res = client.get('/sessionadd')
    assert res.headers['Set-Cookie'].startswith('session=')
    assert res.headers['Vary'] == 'Cookie'

    session_cookie = client.cookies['session']
    client.set_cookie('session', session_cookie)
    res = client.get('/sessioncheck')
    assert res.json == {'test': 'value'}