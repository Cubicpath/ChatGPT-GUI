###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Main networking package for ChatGPT-GUI."""

__all__ = (
    'Action',
    'Client',
    'Conversation',
    'Message',
)

from .chatgpt import Client
from .structures import Action
from .structures import Conversation
from .structures import Message
