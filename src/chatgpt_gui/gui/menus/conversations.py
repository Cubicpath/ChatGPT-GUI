###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Help menu implementation."""
from __future__ import annotations

__all__ = (
    'ConversationsContextMenu',
)

import json
from pathlib import Path

from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...constants import *
from ...network.client import Conversation
from ...utils import add_menu_items
from ...utils import init_objects
from ..aliases import tr
from ..widgets import ConversationTabs
from ..widgets import ConversationView


class ConversationsContextMenu(QMenu):
    """Context menu that shows actions to help the user."""

    def __init__(self, parent: ConversationTabs, current: ConversationView) -> None:
        """Create a new :py:class:`HelpContextMenu`."""
        super().__init__(parent)

        self.tabs = parent
        self.current = current

        init_objects({
            (import_conversation := QAction(self)): {
                'text': tr('gui.menus.conversations.import'),
                'triggered': self.import_conversation
            },
            (export_conversation := QAction(self)): {
                'disabled': current.conversation.uuid is None,
                'text': tr('gui.menus.conversations.export'),
                'triggered': self.export_conversation
            },
            # (rename_conversation := QAction(self)): {
            #     'text': 'gui.menus.conversations.rename',
            #     'triggered': self.rename_conversation
            # }
        })

        add_menu_items(self, [
            'Conversations', import_conversation,
            'Current', export_conversation  # , rename_conversation
        ])

    def import_conversation(self) -> None:
        """Import a conversation from a given file."""
        file_path = Path(QFileDialog.getOpenFileName(
            self, caption=tr('gui.menus.conversations.import'),
            dir=str(CG_CACHE_PATH / 'conversations'),
            filter='JSON Files (*.json);;All files (*.*)')[0])

        # Return if dialog is cancelled
        if not file_path.is_file():
            return

        # Load messages from json data
        conversation = Conversation.from_json(json.loads(file_path.read_text(encoding='utf8')))
        view = ConversationView(conversation)
        for message in conversation.messages:
            if message.role == 'assistant':
                view.receive_message(message, conversation)
            else:
                view.append_to_view(tr('gui.output_text.you_prompt', message.text, key_eval=False))

        # remove empty conversation
        if not self.current.conversation.messages:
            self.tabs.removeTab(self.tabs.currentIndex())

        self.tabs.addTab(view, file_path.stem)
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def export_conversation(self) -> None:
        """Export conversation to given filename."""
        file_path = Path(QFileDialog.getSaveFileName(
            self, caption=tr('gui.menus.conversations.export'),
            dir=str(CG_CACHE_PATH / f'conversations/{self.current.conversation.uuid}.json'),
            filter='JSON Files (*.json);;All files (*.*)')[0])

        # Return if dialog is cancelled
        if str(file_path) == '.':
            return

        file_path.write_text(json.dumps(self.current.conversation.to_json(), indent=2), encoding='utf8')
        self.tabs.setTabText(self.tabs.currentIndex(), file_path.stem)
