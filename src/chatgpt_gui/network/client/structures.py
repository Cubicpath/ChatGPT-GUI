###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Defines the Client structures."""
from __future__ import annotations

__all__ = (
    'Action',
    'Conversation',
    'Message',
    'Session',
    'User',
)

import datetime as dt
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from uuid import UUID
from uuid import uuid4

from ...constants import *


@dataclass
class Message:
    """ChatGPT message sent or received."""

    uuid: UUID = field(default_factory=uuid4)
    text: str | None = field(default=None)
    role: str = field(default='user')

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


@dataclass
class Conversation:
    """ChatGPT conversation.

    Includes a list of all messages sent and received in the conversation.
    """

    uuid: UUID | None = field(default=None)
    messages: list[Message] = field(default_factory=list)

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


@dataclass
class Action:
    """Action sent to ChatGPT.

    If no conversation is provided, ChatGPT creates a new conversation for you in its response.
    """

    model: str
    conversation: Conversation = field(default_factory=Conversation)
    messages: list[Message] = field(default_factory=list)
    parent: Message = field(default_factory=Message)
    type: str = field(default='variant')

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

        if self.conversation.uuid is not None:
            data['conversation_id'] = str(self.conversation.uuid)

        return data


@dataclass
class User:
    """User that is signed-in to ChatGPT."""

    id: str
    name: str
    email: str
    image: str
    picture: str
    groups: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> User:
        """Load data from a JSON representation."""
        return cls(**data)

    def to_json(self) -> dict[str, Any]:
        """Dump data into a JSON representation."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'image': self.image,
            'picture': self.picture,
            'groups': self.groups,
            'features': self.features
        }


@dataclass
class Session:
    """OpenAI Session Data."""

    user: User | None = field(default=None)
    cf_bm: str | None = field(default=None)
    cf_unique_visitor_id: str | None = field(default=None)
    cf_clearance: str | None = field(default=None)
    cf_expires: dt.datetime | None = field(default=None)
    session_expires: dt.datetime | None = field(default=None)
    session_token: str | None = field(default=None)
    user_agent: str | None = field(default=None)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Session:
        """Load data from a JSON representation."""
        cf_data: dict[str, Any] = data.get('cloudflare', {})

        if (user := data.get('user')) is not None:
            if not user:
                user = None
            else:
                user = User.from_json(user)

        if (cf_expires := cf_data.get('expires')) is not None:
            cf_expires = dt.datetime.strptime(cf_expires, CG_DATE_FORMAT)  # type: ignore

        if (session_expires := data.get('expires')) is not None:
            session_expires = dt.datetime.strptime(session_expires, CG_DATE_FORMAT)

        return cls(
            user=user,
            cf_bm=cf_data.get('bm'),
            cf_unique_visitor_id=cf_data.get('unique_visitor_id'),
            cf_clearance=cf_data.get('clearance'),
            cf_expires=cf_expires,
            session_expires=session_expires,
            session_token=data.get('token'),
            user_agent=data.get('user_agent')
        )

    def clear(self) -> None:
        """Clear data while keeping object reference."""
        self.user = None
        self.cf_bm = None
        self.cf_unique_visitor_id = None
        self.cf_clearance = None
        self.cf_expires = None
        self.session_expires = None
        self.session_token = None
        self.user_agent = None

    def is_valid_clearance(self) -> bool:
        """Whether the clearance token exists and is not expired."""
        return bool(self.cf_clearance) and (
            self.cf_expires is not None and
            self.cf_expires >= dt.datetime.now()
        )

    def to_json(self) -> dict[str, Any]:
        """Dump data into a JSON representation."""
        return {
            'user': self.user.to_json() if self.user else {},
            'cloudflare': {
                'bm': self.cf_bm,
                'unique_visitor_id': self.cf_unique_visitor_id,
                'clearance': self.cf_clearance,
                'expires': self.cf_expires.strftime(CG_DATE_FORMAT) if self.cf_expires is not None else None
            },
            'expires': self.session_expires.strftime(CG_DATE_FORMAT) if self.session_expires is not None else None,
            'token': self.session_token,
            'user_agent': self.user_agent
        }
