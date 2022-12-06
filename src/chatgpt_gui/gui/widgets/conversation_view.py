###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ExternalTextBrowser implementation."""
from __future__ import annotations

__all__ = (
    'ConversationView',
)

from PySide6.QtGui import *
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

        self._init_ui()

    def _init_ui(self) -> None:

        def toggle_multiline():
            nonlocal multiline_mode

            if multiline_mode := not multiline_mode:
                input_buttons.insertWidget(2, self.send_button)
                self.input_multi.setText(self.input_line.text())
                self.input_line.clear()
                self.input_line.setHidden(True)
                self.input_multi.setHidden(False)
            else:
                input_layout.insertWidget(2, self.send_button)
                self.input_line.setText(self.input_multi.toPlainText())
                self.input_multi.clear()
                self.input_multi.setHidden(True)
                self.input_line.setHidden(False)

        multiline_mode: bool = True
        self.output = ExternalTextBrowser(self)
        self.input_line = PasteLineEdit(self)
        self.input_multi = QTextEdit(self)
        self.send_button = QPushButton(self)
        self.toggle_multiline_button = QPushButton(self)
        font = QFont('Söhne', 11)

        init_objects({
            self.output: {
                'font': font,
                'placeholderText': tr('gui.output_text.placeholder'),
            },

            self.input_line: {
                'font': font,
                'placeholderText': tr('gui.input_field.placeholder'),
                'returnPressed': self.send_message
            },

            self.input_multi: {
                'font': font,
                'placeholderText': tr('gui.input_field.placeholder'),
            },

            self.send_button: {
                'size': {'fixed': (120, None)},
                'text': tr('gui.send_input', key_eval=False),
                'clicked': self.send_message
            },

            self.toggle_multiline_button: {
                'size': {'fixed': (120, None)},
                'icon': self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
                'text': tr('gui.toggle_multiline', key_eval=False),
                'clicked': toggle_multiline
            }
        })

        init_layouts({
            (input_buttons := QHBoxLayout()): {
                'items': (
                    QSpacerItem(0, 0, hData=QSizePolicy.Policy.MinimumExpanding),
                    self.toggle_multiline_button,
                    self.send_button
                )
            },

            (input_layout := QHBoxLayout()): {
                'items': (self.input_line, self.input_multi)
            },

            QVBoxLayout(self): {
                'items': (self.output, input_layout, input_buttons)
            }

        })

        toggle_multiline()
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
        message: str = self.input_line.text() or self.input_multi.toPlainText()
        self.input_line.clear()
        self.input_multi.clear()
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
