from unittest.mock import MagicMock

from more.browsersession.sessions import SecureCookieSession


def test_open_session(app, request, session_interface):
    session = session_interface.open_session(app, request)
    assert isinstance(session, SecureCookieSession)


def test_save_session(app, request, session_interface):
    response = MagicMock()
    session = session_interface.open_session(app, request)
    content = {'test': 'value'}
    session.update(content)
    session_interface.save_session(app, session, response)
    assert response.set_cookie.called
    payload = response.set_cookie.call_args[0][1]
    serializer = session_interface.get_signing_serializer(app)
    assert serializer.loads(payload) == content