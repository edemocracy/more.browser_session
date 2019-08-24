"""
    more.browser_session
    ~~~~~~~~~~~~~~~~~~~~

    Implements (HTTP, browser) session support for Morepath applications 
    based on cookies signed by itsdangerous. Most code is taken from the 
    Flask project.

    :copyright:
        (c) 2018 Tobias dpausp
        (c) 2013 by Armin Ronacher and contributors.
    :license: BSD, see LICENSE for more details.
"""
from .app import BrowserSessionApp


__all__ = (
    'BrowserSessionApp'
)

