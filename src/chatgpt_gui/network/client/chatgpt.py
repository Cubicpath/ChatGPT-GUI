###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Defines the ChatGPT-GUI HTTP Client."""
from __future__ import annotations

__all__ = (
    'Client',
)

import datetime as dt
import json
import os
from json import JSONDecodeError
from typing import Any
from uuid import UUID

from PySide6.QtCore import *

from ...constants import *
from ...models import CaseInsensitiveDict
from ...utils import decode_url
from ...utils import hide_windows_file
from ..manager import NetworkSession
from ..manager import Request
from ..manager import Response
from .auth import Authenticator
from .structures import Action
from .structures import Conversation
from .structures import Message
from .structures import User


_DATE_FORMAT: str = '%Y-%m-%dT%H:%M:%S.%fZ'


class Client(QObject):
    """Asynchronous HTTP REST Client that interfaces with ChatGPT."""

    authenticationRequired = Signal()
    receivedMessage = Signal(Message, Conversation)
    signedOut = Signal()

    def __init__(self, parent: QObject, **kwargs) -> None:
        """Initialize OpenAI Client.

        Order of precedence for session token::

            1. session_token kwarg value
            2. CHATGPT_SESSION_AUTH environment variable
            3. user's .session config file (Created by application)

        :keyword session_token: Session token, allows for creation of access tokens.
        """
        super().__init__(parent)
        self.receivedMessage.connect(lambda msg, convo: print(f'Conversation: {convo.uuid} | {msg}'))

        self.authenticator = Authenticator(self)
        self.authenticator.authenticationSuccessful.connect(self.new_session)

        self.conversations: dict[UUID, Conversation] = {}
        self.host: str = 'chat.openai.com'
        self.models: list[str] | None = None
        self.user: User | None = None

        self._session_expire: dt.datetime | None = None
        self._first_request: bool = True
        self._access_token: str | None = None

        # Load session token
        self._session_token: str | None = kwargs.pop('session_token', os.getenv('CHATGPT_SESSION_AUTH', None))
        if self._session_token is None and (CG_SESSION_PATH.is_file() or CG_SESSION_PATH_OLD.is_file()):
            # Read from file if value was not provided by kwarg or ENV
            # Migrate old format to new format.
            if CG_SESSION_PATH_OLD.is_file():
                hide_windows_file(CG_SESSION_PATH_OLD, unhide=True)

                # Read old token and dump in new format
                _token_old = CG_SESSION_PATH_OLD.read_text(encoding='utf8')
                CG_SESSION_PATH.write_text(json.dumps({
                    'user': {},
                    'expires': None,
                    'token': _token_old
                }, indent=2), encoding='utf8')

                # Delete old file and mark new file as hidden
                CG_SESSION_PATH_OLD.unlink()
                hide_windows_file(CG_SESSION_PATH)

            try:
                _session_data: dict[str, Any] = json.loads(CG_SESSION_PATH.read_text(encoding='utf8'))

            except JSONDecodeError:
                # Delete session file if invalid json.
                CG_SESSION_PATH.unlink()

            else:
                if user := _session_data.get('user'):
                    self.user = User.from_json(user)

                if expires := _session_data.get('expires'):
                    self._session_expire = dt.datetime.strptime(expires, _DATE_FORMAT)

                self._session_token = _session_data['token']

        self.session: NetworkSession = NetworkSession(self)
        self.session.headers = CaseInsensitiveDict({
            'Accept': '*/*',
            'Accept-Encoding': ', '.join(('gzip', 'deflate', 'br')),
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': self.host,
            'Origin': 'https://chat.openai.com',
            'Referer': 'https://chat.openai.com/chat',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Sec-GPC': '1',
            'TE': 'trailers',
            'User-Agent': CG_USER_AGENT,
            'X-OpenAI-Assistant-App-Id': '',
        })

        if self.session_token:
            self.set_cookie('__Secure-next-auth.session-token', self.session_token)

    @property
    def api_root(self) -> str:
        """Root of sent API requests."""
        return f'https://{self.host}/'

    @property
    def access_token(self) -> str | None:
        """Bearer token to authenticate self to API endpoints."""
        return self._access_token

    @access_token.setter
    def access_token(self, value: str) -> None:
        value = decode_url(value)

        self._access_token = value.strip()
        self.session.headers['Authorization'] = f'Bearer {self._access_token}'

    @access_token.deleter
    def access_token(self) -> None:
        self._access_token = None
        if 'Authorization' in self.session.headers:
            self.session.headers.pop('Authorization')

    @property
    def session_token(self) -> str | None:
        """Bearer token to authenticate self to API endpoints."""
        return self._session_token

    @session_token.setter
    def session_token(self, value: str) -> None:
        value = decode_url(value)

        self._session_token = value.strip()
        self.set_cookie('__Secure-next-auth.session-token', value)

        hide_windows_file(CG_SESSION_PATH, unhide=True)
        CG_SESSION_PATH.write_text(json.dumps({
            'user': self.user.to_json() if self.user is not None else {},
            'expires': self._session_expire.strftime(_DATE_FORMAT) if self._session_expire is not None else None,
            'token': self._session_token
        }, indent=2), encoding='utf8')
        hide_windows_file(CG_SESSION_PATH)

    @session_token.deleter
    def session_token(self) -> None:
        self._session_token = None
        self._session_expire = None
        self.user = None
        self.delete_cookie('__Secure-next-auth.session-token')
        if CG_SESSION_PATH.is_file():
            CG_SESSION_PATH.unlink()

        self.signedOut.emit()

    def _get(self, path: str, update_auth_on_401: bool = True, **kwargs) -> Response:
        """Get a :py:class:`Response` from ChatGPT.

        :param path: path to append to the API root
        :param update_auth_on_401: run self._refresh_auth if response status code is 401 Unauthorized
        :param kwargs: Key word arguments to pass to the requests GET Request.
        """
        if self._first_request:
            self._first_request = False
            self._get('chat')
            self.refresh_auth()

        response: Response = self.session.get(self.api_root + path.strip(), wait_until_finished=True, **kwargs)

        if session_token := self.session.cookies.get('__Secure-next-auth.session-token'):
            self.session_token = session_token

        if response.code and not response.ok:
            # Handle errors
            if response.code == 401 and update_auth_on_401 and self.access_token is not None:
                if self.refresh_auth():
                    response = self._get(path, False, **kwargs)

        return response

    def get_models(self) -> list[dict[str, Any]] | None:
        """Get the list of models to use with ChatGPT.

        :return: List of model data. The "slug" key is the model name.
        """
        return self._get('backend-api/models').json.get('models')

    def send_message(self, message_text: str, conversation: Conversation) -> None:
        """Send a message and emit the AI's response through `the `receivedMessage`` signal.

        Automatically handles the last message id.

        :param message_text: Message to send.
        :param conversation: Conversation to send message in.
        :raises ValueError: If Response couldn't be parsed as a text/event-stream.
        """
        if not self.models:
            if not (models := self.get_models()):
                raise ValueError('Couldn\'t get model data from ChatGPT. Check to make sure you\'re authenticated.')
            self.models = [model['slug'] for model in models]

        if conversation.messages:
            parent_message: Message = conversation.messages[-1]
        else:
            parent_message = Message()

        message: Message = Message(text=message_text)
        action: Action = Action(self.models[0], conversation, [message], parent_message)

        request: Request = Request(
            'POST', self.api_root + 'backend-api/conversation',
            headers={'Accept': 'text/event-stream', 'Content-type': 'application/json'},
            json=action.to_json(), timeout=180.0,
        )

        response: Response = request.send(self.session, wait_until_finished=True)

        # Get the finished stream from the text/event-stream
        # Index -1 Is empty string, as the response ends with 2 newlines
        # Index -2 Is the "[DONE]", signifier
        # Index -3 Is the finished product
        try:
            last_stream: str = response.text.split('\n\n')[-3]
        except IndexError as e:
            raise ValueError(f'Message response is not a text/event-stream ({response.text}).') from e

        json_response: dict[str, Any] = json.loads(last_stream.removeprefix('data: ').strip())
        response_message: Message = Message.from_json(json_response['message'])

        conversation.messages.extend(action.messages)
        conversation.messages.append(response_message)

        if conversation.uuid is None:
            conversation.uuid = UUID(json_response['conversation_id'])

        if conversation.uuid not in self.conversations:
            self.conversations[conversation.uuid] = conversation

        self.receivedMessage.emit(response_message, conversation)

    def hidden_token(self) -> str:
        """:return: The first and last 3 characters of the session token, seperated by periods."""
        key = self.session_token
        if key is not None and len(key) > 6:
            return f'{key[:3]}{"." * 50}{key[-3:]}'
        return 'None'

    def refresh_auth(self) -> bool:
        """Refresh authentication to OpenAI servers.

        If session is invalid, ask for new credentials

        :return: True if successful, else False.
        """
        if not self.session_token or (self._session_expire is not None and self._session_expire < dt.datetime.now()):
            self.authenticationRequired.emit()

            # Delete expired session
            if self.session_token:
                del self.session_token

            return False

        response = self._get('api/auth/session')

        # Ignore next refresh if it has the same value
        if etag := response.headers.get('ETag'):
            self.session.headers['If-None-Match'] = etag

        if user := response.json.get('user'):
            self.user = User.from_json(user)

        if access_token := response.json.get('accessToken'):
            self.access_token = access_token

        if session_expire := response.json.get('expires'):
            self._session_expire = dt.datetime.strptime(session_expire, _DATE_FORMAT)

        if session_token := self.session.cookies.get('__Secure-next-auth.session-token'):
            self.session_token = session_token

        return True

    def signin(self, username: str, password: str) -> None:
        """Signin to OpenAI using the specified username and password.

        :param username: Username to signin to (email address).
        :param password: Password associated with username.
        """
        self.authenticator.username = username
        self.authenticator.password = password
        self.authenticator.authenticate()

    def new_session(self, session_token: str, *_) -> None:
        """Call with new session token provided by authenticator.

        :param session_token: New session token to use.
        """
        self.session_token = session_token
        self.refresh_auth()

    def delete_cookie(self, name: str) -> None:
        """Delete given cookie if cookie exists."""
        self.session.clear_cookies(self.host, '/', name)

    def set_cookie(self, name: str, value: str) -> None:
        """Set cookie value in Cookie jar."""
        self.session.set_cookie(name, value, self.host)
