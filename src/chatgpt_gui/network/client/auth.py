###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Defines the OpenAI authenticator."""
from __future__ import annotations

__all__ = (
    'Authenticator',
)

import re
import base64
from typing import Final
from urllib.parse import quote

from bs4 import BeautifulSoup
from PySide6.QtCore import *
from PySide6.QtGui import *
from tls_client import Session

from ...constants import *
from .structures import User


_STATE_PATTERN: Final[re.Pattern] = re.compile(r'state=(.*)')


class Authenticator(QObject):
    """Object which handles authenticating users to OpenAI.

    Based on https://github.com/rawandahmad698/PyChatGPT
    """

    authenticationFailed = Signal(str, Exception)
    """Emits the username and exception when Authenticator.authenticate() raises an Exception"""

    authenticationSuccessful = Signal(str, User)
    """Emits the session_token on success of Authenticator.authenticate()."""

    captchaEncountered = Signal(QPixmap)
    """Emits a captcha that needs to be solved."""

    solveCaptcha = Signal(str)
    """Emit this signal with the solved captcha from captchaEncountered."""

    def __init__(self, parent: QObject | None = None, username: str | None = None, password: str | None = None):
        """Create a new :py:class:`Authenticator`.

        username and password attributes must be filled out before calling ``authenticate()``.

        :param parent: Parent of QObject instance.
        :param username: Username to login to (email address).
        :param password: Password associated with username.
        """
        super().__init__(parent)

        self.username: str | None = username
        self.password: str | None = password
        self.session = Session(client_identifier='chrome_105')

    def _authenticate(self) -> None:
        """Run all steps.

        :raises ValueError: If Email or password is not provided for Authenticator.
            If csrf token was not provided by endpoint call.
            If auth token was not provided at end of function.

        :raises RuntimeError: If we couldn't get the login page.
            If we couldn't start auth0 login. Could be due to excessive login attempts.
            If there was an unsuccessful request to url provided by signin page.
            If we couldn't access the login state.
            If the email address is not a valid user.
            If password or captcha was wrong.
        """
        # -----------------------------------------------------------------------------------------
        # Step 0:
        # Check that all attributes are valid
        # -----------------------------------------------------------------------------------------
        if not self.username or not self.password:
            raise ValueError('Email or password is not provided for Authenticator.')

        username_encoded: str = quote(self.username)
        password_encoded: str = quote(self.password)

        # -----------------------------------------------------------------------------------------
        # Step 1:
        # Make a request to https://chat.openai.com/auth/login
        # This will block us (403 Request Blocked) early if detected as bot.
        # -----------------------------------------------------------------------------------------
        if self.session.get(url='https://chat.openai.com/auth/login', headers={
            'Host': 'ask.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': CG_USER_AGENT,
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }).status_code != 200:
            raise RuntimeError('Could not get login page.')

        # -----------------------------------------------------------------------------------------
        # Step 2:
        # Get csrf token from endpoint
        # -----------------------------------------------------------------------------------------
        response = self.session.get(url='https://chat.openai.com/api/auth/csrf', headers={
            'Host': 'ask.openai.com',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'User-Agent': CG_USER_AGENT,
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://chat.openai.com/auth/login',
            'Accept-Encoding': 'gzip, deflate, br',
        })

        if 'json' not in response.headers['Content-Type'] or (csrf := response.json()['csrfToken']) is None:
            raise ValueError('csrf token was not provided by endpoint call.')

        # -----------------------------------------------------------------------------------------
        # Step 3:
        # Start auth0 signin process with csrf token
        # This directs us a new url to follow
        # -----------------------------------------------------------------------------------------
        response = self.session.post(url='https://chat.openai.com/api/auth/signin/auth0?prompt=login', headers={
            'Host': 'ask.openai.com',
            'Origin': 'https://chat.openai.com',
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'User-Agent': CG_USER_AGENT,
            'Referer': 'https://chat.openai.com/auth/login',
            'Content-Length': '100',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, data=f'callbackUrl=%2F&csrfToken={csrf}&json=true')

        if response.status_code != 200 or 'json' not in response.headers['Content-Type']:
            raise RuntimeError('Could not start auth0 login. Could be due to excessive login attempts.')

        new_url: str = response.json()['url']

        # -----------------------------------------------------------------------------------------
        # Step 4:
        # Follow new url to obtain our state key
        # -----------------------------------------------------------------------------------------
        response = self.session.get(url=new_url, headers={
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': CG_USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://chat.openai.com/',
        })

        if response.status_code != 302:
            raise RuntimeError(f'Unsuccessful request to given url "{new_url}".')

        state: str = _STATE_PATTERN.findall(response.text)[0].split('"')[0]

        # -----------------------------------------------------------------------------------------
        # Step 5:
        # Go to our state's login page
        # This has a chance to give us a captcha to solve
        # -----------------------------------------------------------------------------------------
        response = self.session.get(f'https://auth0.openai.com/u/login/identifier?state={state}', headers={
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': CG_USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://chat.openai.com/',
        })

        if response.status_code != 200:
            raise RuntimeError('Couldn\'t make request to our login page.')

        captcha: str | None = None
        soup: BeautifulSoup = BeautifulSoup(response.text, 'lxml')
        if soup.find('img', alt='captcha'):
            captcha_svg: str = soup.find('img', alt='captcha')['src'].split(',')[1]  # type: ignore
            decoded_svg: bytes = base64.decodebytes(captcha_svg.encode('ascii'))

            pixmap: QPixmap = QPixmap()
            pixmap.loadFromData(decoded_svg)
            captcha = self.handle_captcha(pixmap)

        # -----------------------------------------------------------------------------------------
        # Step 6:
        # Check if the username (email address) is a valid user
        # Also send the solved captcha if given
        # -----------------------------------------------------------------------------------------
        payload: str = f'state={state}&username={username_encoded}&js-available=false' \
                       f'&webauthn-available=true&is-brave=false&webauthn-platform-available=true&action=default'

        if captcha is not None:
            payload = f'state={state}&username={username_encoded}&captcha={captcha}&js-available=true' \
                      f'&webauthn-available=true&is-brave=false&webauthn-platform-available=true&action=default'

        response = self.session.post(f'https://auth0.openai.com/u/login/identifier?state={state}', headers={
            'Host': 'auth0.openai.com',
            'Origin': 'https://auth0.openai.com',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': CG_USER_AGENT,
            'Referer': f'https://auth0.openai.com/u/login/identifier?state={state}',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, data=payload)

        if response.status_code != 302:
            raise RuntimeError('Email was not a valid user.')

        # -----------------------------------------------------------------------------------------
        # Step 7:
        # Send the email and password to login to the account
        # This will give us our final state in return
        # -----------------------------------------------------------------------------------------
        payload = f'state={state}&username={username_encoded}&password={password_encoded}&action=default'
        response = self.session.post(f'https://auth0.openai.com/u/login/password?state={state}', headers={
            'Host': 'auth0.openai.com',
            'Origin': 'https://auth0.openai.com',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': CG_USER_AGENT,
            'Referer': f'https://auth0.openai.com/u/login/password?state={state}',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, data=payload)

        if response.status_code != 302:
            raise RuntimeError('Password or captcha was wrong.')

        new_state: str = _STATE_PATTERN.findall(response.text)[0].split('"')[0]

        # -----------------------------------------------------------------------------------------
        # Step 8:
        # Finish auth0 process by sending the finished state
        # This will give us our session token in return
        # -----------------------------------------------------------------------------------------
        response = self.session.get(f'https://auth0.openai.com/authorize/resume?state={new_state}', headers={
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': CG_USER_AGENT,
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': f'https://auth0.openai.com/u/login/password?state={state}',
        }, allow_redirects=True)

        if response.status_code != 200:
            raise RuntimeError('Couldn\'t resume authorization state.')

        if not (session_token := self.session.cookies.get('__Secure-next-auth.session-token')):
            raise ValueError('While most of the process was successful, Auth0 didn\'t issue a session token, retry.')

        # -----------------------------------------------------------------------------------------
        # Test success by calling the session endpoint:
        # Emit the session token along with the session's User
        # -----------------------------------------------------------------------------------------
        response = self.session.get('https://chat.openai.com/api/auth/session', headers={
            'Host': 'chat.openai.com',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'User-Agent': CG_USER_AGENT,
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        })

        user: User = User.from_json(response.json()['user'])
        self.authenticationSuccessful.emit(session_token, user)

    def authenticate(self) -> None:
        """Authenticate self to OpenAI using email and password.

        Steps:
            1. Get login page
            2. Get csrf token from endpoint
            3. Post csrf token to signin page
            4. Get state from url returned by login page
            5. Solve CAPTCHA
            6. Post email to signin page
            7. Post email and password to login page to get new state
            8. Resume authorization to finish
        """
        try:
            self._authenticate()
        except Exception as e:
            self.authenticationFailed.emit(self.username, e)

    def handle_captcha(self, image: QPixmap) -> str:
        """Wait for the application implementation to finish the captcha.

        :param image: Captcha image to solve.
        """
        self.solveCaptcha.connect((holder := []).append)
        self.captchaEncountered.emit(image)

        while not holder:
            QCoreApplication.processEvents()

        return holder[0]
