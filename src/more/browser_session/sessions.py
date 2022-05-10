# -*- coding: utf-8 -*-
"""
    more.browser_session.sessions
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Implements cookie based sessions based on itsdangerous.
    Based on the sessions flask.sessions module.

    :copyright: (c) 2018 by Tobias dpausp
    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import hashlib
import logging
import socket
import warnings
from collections.abc import MutableMapping
from datetime import datetime

from itsdangerous import BadSignature, BadPayload, URLSafeTimedSerializer, TimedSerializer
from werkzeug.datastructures import CallbackDict


logg = logging.getLogger(__name__)


def is_ip(value):
    """Determine if the given string is an IP address.

    :param value: value to check
    :type value: str

    :return: True if string is an IP address
    :rtype: bool
    """
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            socket.inet_pton(family, value)
        except socket.error:
            pass
        else:
            return True

    return False


class SessionMixin(MutableMapping):
    """Expands a basic dictionary with session attributes."""

    @property
    def permanent(self):
        """This reflects the ``'_permanent'`` key in the dict."""
        return self.get('_permanent', False)

    @permanent.setter
    def permanent(self, value):
        self['_permanent'] = bool(value)

    #: Some implementations can detect whether a session is newly
    #: created, but that is not guaranteed. Use with caution. The mixin
    # default is hard-coded ``False``.
    new = False

    #: Some implementations can detect changes to the session and set
    #: this when that happens. The mixin default is hard coded to
    #: ``True``.
    modified = True

    #: Some implementations can detect when session data is read or
    #: written and set this when that happens. The mixin default is hard
    #: coded to ``True``.
    accessed = True


class SecureCookieSession(CallbackDict, SessionMixin):
    """Base class for sessions based on signed cookies.

    This session backend will set the :attr:`modified` and
    :attr:`accessed` attributes. It cannot reliably track whether a
    session is new (vs. empty), so :attr:`new` remains hard coded to
    ``False``.
    """

    #: When data is changed, this is set to ``True``. Only the session
    #: dictionary itself is tracked; if the session contains mutable
    #: data (for example a nested dict) then this must be set to
    #: ``True`` manually when modifying that data. The session cookie
    #: will only be written to the response if this is ``True``.
    modified = False

    #: When data is read or written, this is set to ``True``. Used by
    # :class:`.SecureCookieSessionInterface` to add a ``Vary: Cookie``
    #: header, which allows caching proxies to cache different pages for
    #: different users.
    accessed = False

    def __init__(self, initial=None):
        def on_update(self):
            self.modified = True
            self.accessed = True

        super(SecureCookieSession, self).__init__(initial, on_update)

    def __getitem__(self, key):
        self.accessed = True
        return super(SecureCookieSession, self).__getitem__(key)

    def get(self, key, default=None):
        self.accessed = True
        return super(SecureCookieSession, self).get(key, default)

    def setdefault(self, key, default=None):
        self.accessed = True
        return super(SecureCookieSession, self).setdefault(key, default)


class NullSession(SecureCookieSession):
    """Class used to generate nicer error messages if sessions are not
    available.  Will still allow read-only access to the empty session
    but fail on setting.
    """

    def _fail(self, *args, **kwargs):
        raise RuntimeError('The session is unavailable because no secret '
                           'key was set.  Set the secret_key on the '
                           'application to something unique and secret.')
    __setitem__ = __delitem__ = clear = pop = popitem = \
        update = setdefault = _fail
    del _fail


class SessionInterface(object):
    """The basic interface you have to implement in order to replace the
    default session interface which uses werkzeug's securecookie
    implementation.  The only methods you have to implement are
    :meth:`open_session` and :meth:`save_session`, the others have
    useful defaults which you don't need to change.

    The session object returned by the :meth:`open_session` method has to
    provide a dictionary like interface plus the properties and methods
    from the :class:`SessionMixin`.  We recommend just subclassing a dict
    and adding that mixin::

        class Session(dict, SessionMixin):
            pass

    If :meth:`open_session` returns ``None`` the interface will call into
    :meth:`make_null_session` to create a session that acts as replacement
    if the session support cannot work because some requirement is not
    fulfilled.  The default :class:`NullSession` class that is created
    will complain that the secret key was not set.
    """

    #: :meth:`make_null_session` will look here for the class that should
    #: be created when a null session is requested.  Likewise the
    #: :meth:`is_null_session` method will perform a typecheck against
    #: this type.
    null_session_class = NullSession

    #: A flag that indicates if the session interface is pickle based.
    #: This can be used by to make a decision in regards to how to deal 
    #: with the session object.
    pickle_based = False

    def make_null_session(self, app):
        """Creates a null session which acts as a replacement object if the
        real session support could not be loaded due to a configuration
        error.  This mainly aids the user experience because the job of the
        null session is to still support lookup without complaining but
        modifications are answered with a helpful error message of what
        failed.

        This creates an instance of :attr:`null_session_class` by default.
        """
        return self.null_session_class()

    def is_null_session(self, obj):
        """Checks if a given object is a null session.  Null sessions are
        not asked to be saved.

        This checks if the object is an instance of :attr:`null_session_class`
        by default.
        """
        return isinstance(obj, self.null_session_class)

    def get_cookie_domain(self, app):
        """Returns the domain that should be set for the session cookie.

        Uses ``browser_session.cookie_domain`` if it is configured, otherwise
        falls back to detecting the domain based on ``app.server_name``.

        Once detected (or if not set at all), ``browser_session.cookie_domain`` is
        updated to avoid re-running the logic.
        """
        rv = app.settings.browser_session.cookie_domain

        # set explicitly, or cached from SERVER_NAME detection
        # if False, return None
        if rv is not None:
            return rv if rv else None

        try:
            rv = app.settings.app.server_name
        except AttributeError:
            return None

        # chop off the port which is usually not supported by browsers
        # remove any leading '.' since we'll add that later
        rv = rv.rsplit(':', 1)[0].lstrip('.')

        if '.' not in rv:
            # Chrome doesn't allow names without a '.'
            # this should only come up with localhost
            # hack around this by not setting the name, and show a warning
            warnings.warn(
                '"{rv}" is not a valid cookie domain, it must contain a ".".'
                ' Add an entry to your hosts file, for example'
                ' "{rv}.localdomain", and use that instead.'.format(rv=rv)
            )
            return None

        ip = is_ip(rv)

        if ip:
            warnings.warn(
                'The session cookie domain is an IP address. This may not work'
                ' as intended in some browsers. Add an entry to your hosts'
                ' file, for example "localhost.localdomain", and use that'
                ' instead.'
            )

        # if this is not an ip and app is mounted at the root, allow subdomain
        # matching by adding a '.' prefix
        if self.get_cookie_path(app) == '/' and not ip:
            rv = '.' + rv

        return rv

    def get_cookie_name(self, app):
        """Returns the name of the cookie. The default value is 'session'.
        """
        return app.settings.browser_session.cookie_name

    def get_cookie_path(self, app):
        """Returns the path for which the cookie should be valid.  The
        default implementation uses the value from the ``browser_session.cookie_path``
        config var if it's set, and falls back to ``app.root`` or
        uses ``/`` if it's ``None``.
        """
        return app.settings.browser_session.cookie_path or app.settings.app.root

    def get_cookie_httponly(self, app):
        """Returns True if the session cookie should be httponly.  This
        currently just returns the value of the ``browser_session.cookie_httponly``
        config var.
        """
        return app.settings.browser_session.cookie_httponly

    def get_cookie_secure(self, app):
        """Returns True if the cookie should be secure.  This currently
        just returns the value of the ``browser_session.cookie_secure`` setting.
        """
        return app.settings.browser_session.cookie_secure

    def get_expiration_time(self, app, session):
        """A helper method that returns an expiration date for the session
        or ``None`` if the session is linked to the browser session.  The
        default implementation returns now + the permanent session
        lifetime configured on the application.
        """
        if session.permanent:
            return datetime.utcnow() + app.settings.browser_session.permanent_lifetime

    def should_set_cookie(self, app, session):
        """Used by session backends to determine if a ``Set-Cookie`` header
        should be set for this session cookie for this response. If the session
        has been modified, the cookie is set. If the session is permanent and
        the ``browser_session.refresh_each_request`` config is true, the cookie is
        always set.

        This check is usually skipped if the session was deleted.
        """

        return session.modified or (
            session.permanent and app.settings.browser_session.refresh_each_request
        )

    def open_session(self, app, request):
        """This method has to be implemented and must either return ``None``
        in case the loading failed because of a configuration error or an
        instance of a session object which implements a dictionary like
        interface + the methods and attributes on :class:`SessionMixin`.
        """
        raise NotImplementedError()

    def save_session(self, app, session, response):
        """This is called for actual sessions returned by :meth:`open_session`
        at the end of the request.  This is still called during a request
        context so if you absolutely need access to the request you can do
        that.
        """
        raise NotImplementedError()


class SecureCookieSessionInterface(SessionInterface):
    """The default session interface that stores sessions in signed cookies
    through the :mod:`itsdangerous` module.
    """
    #: the salt that should be applied on top of the secret key for the
    #: signing of cookie based sessions.
    salt = 'cookie-session'
    #: the hash function to use for the signature.  The default is sha1
    digest_method = staticmethod(hashlib.sha1)
    #: the name of the itsdangerous supported key derivation.  The default
    #: is hmac.
    key_derivation = 'hmac'
    #: A python serializer for the payload.  The default is o compact
    #: JSON derived serializer with support for some extra Python types
    #: such as datetime objects or tuples.
    session_class = SecureCookieSession

    #: itsdangerous serializer class to use, default is URLSafeTimedSerializer
    serializer_class = URLSafeTimedSerializer

    
    def secret_key(self, app):
        try:
            return app.settings.browser_session.secret_key
        except AttributeError:
            raise Exception('no secret key set (browser_session.secret_key), cannot use secure sessions!')

    def get_signing_serializer(self, app):
        signer_kwargs = dict(
            key_derivation=self.key_derivation,
            digest_method=self.digest_method
        )
        return self.serializer_class(self.secret_key(app), salt=self.salt, signer_kwargs=signer_kwargs)

    def open_session(self, app, request):
        s = self.get_signing_serializer(app)
        if s is None:
            return None
        val = request.cookies.get(self.get_cookie_name(app))
        if not val:
            return self.session_class()
        max_age = app.settings.browser_session.permanent_lifetime
        try:
            data = s.loads(val, max_age=max_age)
            return self.session_class(data)
        except BadSignature:
            logg.warn('bad session cookie signature, is someone attacking us?')
            return self.session_class()
        except BadPayload:
            logg.info('bad session cookie payload from client, ignoring')
            return self.session_class()

    def save_session(self, app, session, response):
        name = self.get_cookie_name(app)
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        # If the session is modified to be empty, remove the cookie.
        # If the session is empty, return without setting the cookie.
        if not session:
            if session.modified:
                response.delete_cookie(name=name, domain=domain, path=path)

            return

        # Add a "Vary: Cookie" header if the session was accessed at all.
        if session.accessed:
            response.vary = ['Cookie']

        if not self.should_set_cookie(app, session):
            return

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        expires = self.get_expiration_time(app, session)
        val = self.get_signing_serializer(app).dumps(dict(session))
        response.set_cookie(
            name,
            val,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            expires=expires
        )
