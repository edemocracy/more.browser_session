import morepath
from pytest import fixture
import webob
from webtest import TestApp as Client

from more.browsersession.app import BrowserSessionApp
from more.browsersession.sessions import SecureCookieSessionInterface



SETTINGS = {
    'browsersession': {
        'secret_key': 'test'
    }
}


@fixture(scope='session')
def test_app_class():
    class TestApp(BrowserSessionApp):
        def test_request(self):
            return webob.request.BaseRequest.blank('/')

    @TestApp.path('/sessionadd')
    class SessionAdd:
        pass

    @TestApp.view(SessionAdd)
    def session_add(_self, request):
        request.browsersession['test'] = 'value'

    @TestApp.path('/sessioncheck')
    class SessionCheck:
        pass

    @TestApp.json(SessionCheck)
    def session_check(_self, request):
        return request.browsersession
        

    return TestApp


@fixture(scope='session')
def app(test_app_class):
    morepath.autoscan()
    test_app_class.init_settings(SETTINGS)
    test_app_class.commit()

    app = test_app_class()
    return app


@fixture(scope='session')
def client(app):
    return Client(app)


@fixture
def request(app):
    return app.test_request()


@fixture
def session_interface():
    return SecureCookieSessionInterface()
