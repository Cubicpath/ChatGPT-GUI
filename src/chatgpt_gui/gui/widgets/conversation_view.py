###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ExternalTextBrowser implementation."""
from __future__ import annotations

__all__ = (
    'ConversationView',
)

from ...network.client import Conversation
from ...network.client import Message
from ..aliases import app
from ..aliases import tr
from .external_text_browser import ExternalTextBrowser


class ConversationView(ExternalTextBrowser):
    """Viewer for a ChatGPT conversation."""

    def __init__(self, conversation: Conversation | None = None, *args, **kwargs) -> None:
        """Initialize :py:class:`ConversationView` values."""
        super().__init__(*args, **kwargs)
        self.conversation = conversation if conversation is not None else Conversation()
        self.setPlaceholderText(tr('gui.output_text.placeholder'))

        app().client.receivedMessage.connect(self.receive_message)

    def append_to_view(self, text: str) -> None:
        """Append some new text to the output.

        Adds two newlines after the text for better differentiation between messages.
        Also scrolls down to bottom for you.

        :param text: Text to append to output.
        :param view: The ConversationView to append text to.
        """
        self.setText(f'{self.toPlainText()}{text}\n\n')
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def receive_message(self, message: Message, conversation: Conversation) -> None:
        """Receive a response from the client.

        :param message: Message received.
        :param conversation: Conversation received in.
        """
        if conversation is self.conversation:
            self.append_to_view(tr('gui.output_text.ai_prompt', message.text, key_eval=False))
