"""
    more.browsersession.app
    ~~~~~~~~~~~~~~~~~~~~~~~

    Session app, tween and associated app settings.

    :copyright: (c) 2018 by Tobias dpausp
    :license: BSD, see LICENSE for more details.
"""
import morepath
from more.browsersession.sessions import SecureCookieSessionInterface

class BrowserSessionApp(morepath.App):

    """
    Subclass this if you want support for HTTP sessions in your Morepath app.
    """
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.browsersession_interface = SecureCookieSessionInterface()


@BrowserSessionApp.setting_section(section='browsersession')
def get_browsersession_settings():
    return {
        'cookie_name': 'session',
        'cookie_domain': None,
        'cookie_path': '/',
        'cookie_secure': True,
        'cookie_httponly': True,
        'refresh_each_request': False,
        'permanent_lifetime': 3600
    }


@BrowserSessionApp.tween_factory()
def browsersession_tween_factory(app, handler):
    def browsersession_tween(request):
        session_interface = app.browsersession_interface
        session = session_interface.open_session(app, request)
        if session is None:
            session = session_interface.make_null_session(app)

        request.browsersession = session
        response = handler(request)

        if not session_interface.is_null_session(session):
            session_interface.save_session(app, session, response)

        return response

    return browsersession_tween
