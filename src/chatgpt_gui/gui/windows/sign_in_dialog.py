###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""PasteLineEdit implementation."""
from __future__ import annotations

__all__ = (
    'SignInDialog',
)

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...models import DeferredCallable
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app


class SignInDialog(QWidget):
    """A :py:class:`SignInDialog` which signs in to the ChatGPT Client."""

    def __init__(self) -> None:
        """Create a new :py:class:`SignInDialog`."""
        super().__init__(None)

        app().client.authenticator.authenticationSuccessful.connect(self.close)
        app().client.authenticator.authenticationFailed.connect(DeferredCallable(self._reset_fields))

        self._init_ui()

    def _init_ui(self) -> None:
        username_label = QLabel()
        password_label = QLabel()
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.set_username_button = QPushButton(self)
        self.set_password_button = QPushButton(self)
        self.sign_in_button = QPushButton(self)

        init_objects({
            self: {
                'size': {'fixed': (500, 200)},
                'windowFlags': Qt.WindowType.Dialog,
                'windowModality': Qt.WindowModality.ApplicationModal,
                'windowIcon': app().icon_store['account'],
            },

            self.username_input: {
                'returnPressed': self._enter_username,
            },

            self.password_input: {
                'echoMode': QLineEdit.EchoMode.Password,
                'returnPressed': self._enter_password,
            },

            self.sign_in_button: {
                'clicked': DeferredCallable(
                    app().client.signin,
                    self.username_input.text,
                    self.password_input.text
                ),
            },

            self.set_username_button: {
                'size': {'minimum': (45, None)},
                'clicked': self._enter_username,
            },

            self.set_password_button: {
                'size': {'minimum': (45, None)},
                'clicked': self._enter_password,
            },

            (reset_fields_button := QPushButton(self)): {
                'clicked': self._reset_fields,
            },

            (cancel_button := QPushButton(self)): {
                'clicked': self.close,
            }
        })

        app().init_translations({
            self.setWindowTitle: 'gui.sign_in_dialog.title',
            username_label.setText: 'gui.sign_in_dialog.username_label',
            password_label.setText: 'gui.sign_in_dialog.password_label',
            self.username_input.setPlaceholderText: 'gui.sign_in_dialog.username_placeholder',
            self.password_input.setPlaceholderText: 'gui.sign_in_dialog.password_placeholder',

            self.set_username_button.setText: 'gui.sign_in_dialog.set_field',
            self.set_password_button.setText: 'gui.sign_in_dialog.set_field',
            self.sign_in_button.setText: 'gui.sign_in_dialog.sign_in',
            reset_fields_button.setText: 'gui.sign_in_dialog.reset_fields',
            cancel_button.setText: 'gui.sign_in_dialog.cancel'
        })

        init_layouts({
            (input_layout := QGridLayout()): {
                'items': (
                    (username_label, 1, 0),
                    (self.username_input, 1, 1),
                    (self.set_username_button, 1, 2),
                    (password_label, 2, 0),
                    (self.password_input, 2, 1),
                    (self.set_password_button, 2, 2)
                )
            },

            (bottom := QHBoxLayout()): {
                'items': (reset_fields_button, cancel_button)
            },

            # Main layout
            QVBoxLayout(self): {
                'items': (input_layout, self.sign_in_button, bottom)
            }
        })

        input_layout.setRowMinimumHeight(2, 40)
        input_layout.setRowStretch(3, 1)
        input_layout.setColumnMinimumWidth(1, 200)
        input_layout.setSpacing(5)

    def _enter_username(self) -> None:
        self.username_input.setDisabled(True)
        self.set_username_button.setDisabled(True)

        self.password_input.setDisabled(False)
        self.set_password_button.setDisabled(False)
        self.password_input.setFocus()

    def _enter_password(self) -> None:
        self.password_input.setDisabled(True)
        self.set_password_button.setDisabled(True)

        self.sign_in_button.setDisabled(False)
        self.sign_in_button.setFocus()

    def _reset_fields(self) -> None:
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setDisabled(False)
        self.password_input.setDisabled(True)

        self.set_username_button.setDisabled(False)
        self.set_password_button.setDisabled(True)

        self.sign_in_button.setDisabled(True)

    def showEvent(self, event: QShowEvent) -> None:
        """Reset fields when dialog is shown to user."""
        super().showEvent(event)
        self._reset_fields()
