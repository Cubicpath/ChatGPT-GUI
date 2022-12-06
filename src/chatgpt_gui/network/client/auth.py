###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Defines the OpenAI authenticator."""
from __future__ import annotations

__all__ = (
    'Authenticator',
)

import re

from PySide6.QtCore import *
from PySide6.QtGui import *

from ..manager import NetworkSession
from ..manager import Response


class Authenticator(QObject):
    """Object which handles authenticating users to OpenAI.

    Based on https://github.com/rawandahmad698/PyChatGPT
    """

    captchaEncountered = Signal(QPixmap)
    solveCaptcha = Signal(str)

    def __init__(self, parent: QObject | None = None, email: str | None = None, password: str | None = None):
        """Create a new :py:class:`Authenticator`.

        email and password attributes must be filled out before calling ``authenticate()``.
        """
        super().__init__(parent)
        self.email: str | None = email
        self.password: str | None = password
        self.session: NetworkSession = NetworkSession(self)
        self.session.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Encoding': ', '.join(('gzip', 'deflate', 'br')),
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': 'chat.openai.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Sec-GPC': '1',
            'TE': 'trailers',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
        }

    def authenticate(self) -> None:
        """Authenticate self to OpenAI using email and password.

        Steps:
            1. Get login page
            2. Get auth0 urls
            3. Get csrf token from endpoint
            4. Post csrf token to signin page [FAILS 403]
            5. Get state from url returned by login page
            6. Solve CAPTCHA (not implemented)
            7. Post email to signin page
            8. Post email and password to login page to get new state
            9. Resume authorization to finish

        :raises ValueError: If Email or password is not provided for Authenticator.
            If csrf token was not provided by endpoint call.

        :raises RuntimeError: If we couldn't get the login page.
            If we couldn't start auth0 login. Could be due to excessive login attempts.
            If there was an unsuccessful request to url provided by signin page.
            If the email address is not a valid user.
            If password or captcha was wrong.
        """
        if not self.email or not self.password:
            raise ValueError('Email or password is not provided for Authenticator.')

        # Make a request to https://chat.openai.com/auth/login
        if not self.session.get('https://chat.openai.com/auth/login', wait_until_finished=True).ok:
            raise RuntimeError('Could not get login page.')

        # Get auth0 urls
        response: Response = self.session.get('https://chat.openai.com/api/auth/providers', wait_until_finished=True)
        signin_url: str = response.json['auth0']['signinUrl']      # 'https://chat.openai.com/api/auth/signin/auth0'
        callback_url: str = response.json['auth0']['callbackUrl']  # 'https://chat.openai.com/api/auth/callback/auth0'

        # Get csrf token from endpoint
        response: Response = self.session.get('https://chat.openai.com/api/auth/csrf', wait_until_finished=True)
        if 'json' not in response.headers['Content-Type'] or (csrf := response.json['csrfToken']) is None:
            raise ValueError('csrf token was not provided by endpoint call.')

        # Start auth0 login with csrf token
        # This currently returns 403 Request Blocked
        response = self.session.post(
            signin_url,
            params={'prompt': 'login', 'redirect_uri': callback_url},
            headers={
                'Accept': '*/*',
                'Content-Length': '100',
                'Origin': 'https://chat.openai.com',
                'Referer': 'https://chat.openai.com/auth/login'
            }, data={
                'callbackUrl': callback_url,
                'csrfToken': csrf,
                'json': 'true'
            },
            wait_until_finished=True
        )

        if not response.ok or 'json' not in response.headers['Content-Type']:
            raise RuntimeError('Could not start auth0 login. Could be due to excessive login attempts.')

        # Head to the given url to obtain our login state
        next_url = response.json['url']
        self.session.headers['Host'] = 'auth0.openai.com'
        self.session.headers['Referer'] = 'https://chat.openai.com/'

        response = self.session.get(next_url, wait_until_finished=True)

        if response.code != 302:
            raise RuntimeError(f'Unsuccessful request to given url "{next_url}".')

        state: str = self.session.cookies['__Secure-next-auth.state']

        # Use the state to get our login page
        login_url = f'https://auth0.openai.com/u/login/identifier?state={state}'
        self.session.get(login_url, wait_until_finished=True)

        captcha: str | None = None
        # captcha = self.handle_captcha()

        check_user_data = {
            'state': state,
            'username': self.email,
            'js-available': 'true',
            'webauthn-available': 'true',
            'is-brave': 'false',
            'webauthn-platform-available': 'true',
            'action': 'default'
        }

        if captcha is not None:
            check_user_data['captcha'] = captcha

        self.session.headers['Origin'] = 'https://auth0.openai.com'

        # Continue auth0 login with state and solved captcha
        response = self.session.post(
            signin_url,
            params={'prompt': 'login'},
            headers={'Referer': login_url}, data=check_user_data,
            wait_until_finished=True
        )

        if response.code != 302:
            raise RuntimeError('Email was not a valid user.')

        # Enter password and get new login state
        password_url = f'https://auth0.openai.com/u/login/password?state={state}'
        self.session.headers['Referer'] = password_url

        response = self.session.post(
            password_url,
            data={
                'state': state,
                'username': self.email,
                'password': self.password,
                'action': 'default'
            },
            wait_until_finished=True
        )

        if response.code != 302:
            raise RuntimeError('Password or captcha was wrong.')

        new_state = re.findall(r'state=(.*)', response.text)[0].split('"')[0]

        response = self.session.get(
            'https://auth0.openai.com/authorize/resume',
            params={'state': new_state},
            wait_until_finished=True
        )

    def handle_captcha(self, image: QPixmap) -> str:
        """Wait for the application implementation to finish the captcha.

        :param image: Captcha image to solve.
        """
        self.solveCaptcha.connect((holder := []).append)
        self.captchaEncountered.emit(image)

        while not holder:
            QCoreApplication.processEvents()

        return holder[0]
