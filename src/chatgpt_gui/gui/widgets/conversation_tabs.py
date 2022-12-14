###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ConversationView implementation."""
from __future__ import annotations

__all__ = (
    'ConversationTabs',
)

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...network.client import Conversation
from ...utils import init_objects
from ..aliases import app
from .conversation_view import ConversationView


class ConversationTabs(QTabWidget):
    """Viewer for a ChatGPT conversation."""

    def __init__(self, parent: QWidget | None = None, conversation: Conversation | None = None) -> None:
        """Initialize :py:class:`ConversationView` values."""
        super().__init__(parent)
        self.conversation_counter: int = 0
        self.conversation: Conversation = conversation if conversation is not None else Conversation()
        self.add_conversation_button: QPushButton = QPushButton(self)

        init_objects({
            self: {
                'tabsClosable': True,
                'tabCloseRequested': self.remove_conversation,
                'contextMenuPolicy': Qt.ContextMenuPolicy.CustomContextMenu,
                'customContextMenuRequested': self.on_custom_context_menu
            },

            self.add_conversation_button: {
                'size': {'fixed': (None, 26)},
                'icon': app().icon_store['add'],
                'clicked': self.add_conversation
            }
        })

        self.setCornerWidget(self.add_conversation_button, Qt.Corner.TopLeftCorner)

    def add_conversation(self):
        """Add a new conversation. Increments the conversation counter."""
        self.conversation_counter += 1
        self.addTab(ConversationView(), f'Conversation {self.conversation_counter}')

    def remove_conversation(self, index: int):
        """Remove the conversation at the given index.

        :param index: Index of conversation to remove.
        """
        view: ConversationView = self.conversation_tabs.widget(index)  # type: ignore
        view.deleteLater()

        self.removeTab(index)
        if not self.count():
            self.conversation_counter = 0
            self.add_conversation()

    def on_custom_context_menu(self, point: QPoint) -> None:
        """Ran when the customContextMenuRequested signal is emitted.

        :param point: The point to place the context menu.
        """
