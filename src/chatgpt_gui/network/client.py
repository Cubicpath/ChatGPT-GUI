###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Defines the ChatGPT-GUI HTTP Client."""
from __future__ import annotations

__all__ = (
    'Action',
    'Client',
    'Conversation',
    'Message',
)

import json
import os
from typing import Any
from typing import NamedTuple
from uuid import UUID
from uuid import uuid4

from PySide6.QtCore import *

from ..constants import *
from ..models import CaseInsensitiveDict
from ..utils import decode_url
from ..utils import hide_windows_file
from .manager import NetworkSession
from .manager import Request
from .manager import Response


class Message(NamedTuple):
    """ChatGPT message sent or received."""

    uuid: UUID
    text: str | None = None
    role: str = 'user'

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Message:
        """Load data from a JSON representation."""
        return cls(
            uuid=UUID(data['id']),
            text='\n\n'.join(data['content']['parts']),
            role=data['role']
        )

    def to_json(self) -> dict[str, Any]:
        """Dump data into a JSON representation.

        The ``content`` key is omitted if the ``text`` attribute is ``None``.
        """
        data: dict[str, Any] = {
            'id': str(self.uuid),
            'role': self.role
        }

        if self.text is not None:
            data['content'] = {
                'content_type': 'text',
                'parts': [self.text]
            }

        return data


class Conversation(NamedTuple):
    """ChatGPT conversation.

    Includes a list of all messages sent and received in the conversation.
    """

    uuid: UUID
    messages: list[Message]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Conversation:
        """Load data from a JSON representation."""
        return cls(
            uuid=UUID(data['id']),
            messages=[Message.from_json(message) for message in data['messages']],
        )

    def to_json(self) -> dict[str, Any]:
        """Dump data into a JSON representation."""
        return {
            'id': str(self.uuid),
            'messages': [message.to_json() for message in self.messages],
        }


class Action(NamedTuple):
    """Action sent to ChatGPT.

    If no conversation is provided, ChatGPT creates a new conversation for you in its response.
    """

    messages: list[Message]
    parent: Message
    model: str
    conversation: Conversation | None = None
    type: str = 'next'

    def to_json(self) -> dict[str, Any]:
        """Dump data into a JSON representation.

        The ``conversation_id`` key is omitted if the ``conversation`` attribute is ``None``.
        """
        data = {
            'action': self.type,
            'messages': [message.to_json() for message in self.messages],
            'model': self.model,
            'parent_message_id': str(self.parent.uuid)
        }

        if self.conversation is not None:
            data['conversation_id'] = str(self.conversation.uuid)

        return data


class Client(QObject):
    """Asynchronous HTTP REST Client that interfaces with ChatGPT."""

    receivedMessage = Signal(str)

    def __init__(self, parent: QObject, **kwargs) -> None:
        """Initialize OpenAI Client.

        Order of precedence for session token::

            1. session_token kwarg value
            2. CHATGPT_SESSION_AUTH environment variable
            3. user's .session config file (Created by application)

        :keyword session_token: Session token, allows for creation of access tokens.
        """
        super().__init__(parent)
        self.receivedMessage.connect(print)

        self._conversation: Conversation | None = None
        self.conversations: dict[UUID, Conversation] = {}
        self.host: str = 'chat.openai.com'
        self.models: list[str] | None = None

        self._first_request: bool = True
        self._access_token: str | None = None
        self._session_token: str | None = kwargs.pop('session_token', os.getenv('CHATGPT_SESSION_AUTH', None))
        if self._session_token is None and CG_SESSION_PATH.is_file():
            self._session_token = CG_SESSION_PATH.read_text(encoding='utf8').strip()

        self.session: NetworkSession = NetworkSession(self)
        self.session.headers = CaseInsensitiveDict({
            'Accept': '*/*',
            'Accept-Encoding': ', '.join(('gzip', 'deflate', 'br')),
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': self.host,
            'If-None-Match': 'zh3ivhmesm13w',
            'Origin': 'https://chat.openai.com',
            'Referer': 'https://chat.openai.com/chat',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Sec-GPC': '1',
            'TE': 'trailers',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
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
    def conversation(self) -> Conversation | None:
        """Return the current conversation."""
        return self._conversation

    @conversation.setter
    def conversation(self, value: Conversation) -> None:
        self._conversation = self.conversations[value.uuid] = value

    @conversation.deleter
    def conversation(self) -> None:
        if self._conversation is None:
            raise ValueError('Cannot delete a null conversation.')

        del self.conversations[self._conversation.uuid]
        self._conversation = None

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
        CG_SESSION_PATH.write_text(self._session_token, encoding='utf8')
        hide_windows_file(CG_SESSION_PATH)

    @session_token.deleter
    def session_token(self) -> None:
        self._session_token = None
        self.delete_cookie('__Secure-next-auth.session-token')
        if CG_SESSION_PATH.is_file():
            CG_SESSION_PATH.unlink()

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
                self.refresh_auth()
                response = self._get(path, False, **kwargs)

        return response

    def get_models(self) -> list[dict[str, Any]]:
        """Get the list of models to use with ChatGPT.

        :return: List of model data. The "slug" key is the model name.
        """
        return self._get('backend-api/models').json['models']

    def send_message(self, message_text: str) -> None:
        """Send a message and emit the AI's response through `the `receivedMessage`` signal.

        Automatically handles the conversation id and last message id.

        :param message_text: Message to send.
        :raises ValueError: If Response couldn't be parsed as a text/event-stream.
        """
        if self.models is None:
            self.models = [model['slug'] for model in self.get_models()]

        if self.conversation is not None and self.conversation.messages:
            parent_message: Message = self.conversation.messages[-1]
        else:
            parent_message = Message(uuid4())

        message: Message = Message(uuid4(), message_text)
        action: Action = Action([message], parent_message, self.models[0], self.conversation)

        request: Request = Request(
            'POST', self.api_root + 'backend-api/conversation',
            headers={'Accept': 'text/event-stream', 'Content-type': 'application/json'},
            json=action.to_json(), timeout=60.0,
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

        convo_id: UUID = UUID(json_response['conversation_id'])
        convo = self.conversation = self.conversations.get(convo_id, Conversation(convo_id, []))
        convo.messages.extend(action.messages)
        convo.messages.append(response_message)

        self.receivedMessage.emit(response_message.text)

    def hidden_token(self) -> str:
        """:return: The first and last 3 characters of the session token, seperated by periods."""
        key = self.session_token
        if key is not None and len(key) > 6:
            return f'{key[:3]}{"." * 50}{key[-3:]}'
        return 'None'

    def refresh_auth(self) -> None:
        """Refresh authentication to OpenAI servers.

        token MUST have a value for this to work.
        """
        response = self._get('api/auth/session')

        if session_token := self.session.cookies.get('__Secure-next-auth.session-token'):
            self.session_token = session_token

        if token := response.json.get('accessToken'):
            self.access_token = token

    def delete_cookie(self, name: str) -> None:
        """Delete given cookie if cookie exists."""
        self.session.clear_cookies(self.host, '/', name)

    def set_cookie(self, name: str, value: str) -> None:
        """Set cookie value in Cookie jar."""
        self.session.set_cookie(name, value, self.host)
