"""
    more.browser_session.app
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Session app, tween and associated app settings.

    :copyright: (c) 2018 by Tobias dpausp
    :license: BSD, see LICENSE for more details.
"""
import morepath
from more.browser_session.sessions import SecureCookieSessionInterface

class BrowserSessionApp(morepath.App):

    """
    Subclass this if you want support for HTTP sessions in your Morepath app.
    """
    def __init__(self, *_args, **_kwargs):
        self.browser_session_interface = SecureCookieSessionInterface()


@BrowserSessionApp.setting_section(section='browser_session')
def get_browser_session_settings():
    return {
        'cookie_name': 'session',
        'cookie_domain': None,
        'cookie_path': '/',
        'cookie_secure': True,
        'cookie_httponly': True,
        'refresh_each_request': False,
        'permanent_lifetime': 3600
    }


@BrowserSessionApp.tween_factory(over=morepath.core.poisoned_host_header_protection_tween_factory)
def browser_session_tween_factory(app, handler):
    def browser_session_tween(request):
        session_interface = app.browser_session_interface
        session = session_interface.open_session(app, request)
        if session is None:
            session = session_interface.make_null_session(app)

        request.browser_session = session
        response = handler(request)

        if not session_interface.is_null_session(session):
            session_interface.save_session(app, session, response)

        return response

    return browser_session_tween
