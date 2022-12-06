###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ExternalTextBrowser implementation."""
from __future__ import annotations

__all__ = (
    'ConversationView',
)

from PySide6.QtWidgets import *

from ...network.client import Conversation
from ...network.client import Message
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app
from ..aliases import tr
from .external_text_browser import ExternalTextBrowser
from .paste_line_edit import PasteLineEdit


class ConversationView(QFrame):
    """Viewer for a ChatGPT conversation."""

    def __init__(self, conversation: Conversation | None = None, *args, **kwargs) -> None:
        """Initialize :py:class:`ConversationView` values."""
        super().__init__(*args, **kwargs)
        self.conversation = conversation if conversation is not None else Conversation()
        self.output = ExternalTextBrowser(self)
        self.input = PasteLineEdit(self)
        self.send_button = QPushButton(self)

        init_objects({
            self.output: {
                'placeholderText': tr('gui.output_text.placeholder')
            },

            self.input: {
                'placeholderText': tr('gui.input_field.placeholder'),
                'returnPressed': self.send_message
            },

            self.send_button: {
                'size': {'fixed': (60, None)},
                'text': 'Send',
                'clicked': self.send_message
            }
        })

        init_layouts({
            (a := QHBoxLayout()): {
                'items': (self.input, self.send_button)
            },

            QVBoxLayout(self): {
                'items': (self.output, a)
            }
        })

        self.output.setPlaceholderText(tr('gui.output_text.placeholder'))

        app().client.receivedMessage.connect(self.receive_message)

    def append_to_view(self, text: str) -> None:
        """Append some new text to the output.

        Adds two newlines after the text for better differentiation between messages.
        Also scrolls down to bottom for you.

        :param text: Text to append to output.
        """
        self.output.setText(f'{self.output.toPlainText()}{text}\n\n')
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def send_message(self) -> None:
        """Send a message to the client using the current input text.

        Clears the input and disables after sending.
        """
        message: str = self.input.text()
        self.input.clear()
        self.send_button.setDisabled(True)
        self.append_to_view(tr('gui.output_text.you_prompt', message, key_eval=False))  # type: ignore

        app().client.send_message(message, self.conversation)  # type: ignore

    def receive_message(self, message: Message, conversation: Conversation) -> None:
        """Receive a response from the client.

        :param message: Message received.
        :param conversation: Conversation received in.
        """
        if conversation is self.conversation:
            self.send_button.setDisabled(False)
            self.append_to_view(tr('gui.output_text.ai_prompt', message.text, key_eval=False))
