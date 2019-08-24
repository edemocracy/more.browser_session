more.browser_session
====================

WARNING: This is an early version that works for me. Please don't rely on it ;)

Implements (HTTP, browser) session support for Morepath applications based on cookies signed by itsdangerous.
Most code is taken from the Flask project.

The session data is signed, not encrypted! Don't store sensitive data in the session!
Support for encryption will be added soon.
