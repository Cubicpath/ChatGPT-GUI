###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Defines the Client structures."""
from __future__ import annotations

__all__ = (
    'Action',
    'Conversation',
    'Message',
    'User',
)

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from uuid import UUID
from uuid import uuid4


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
    type: str = field(default='next')

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
