###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""CaptchaDialog implementation."""
from __future__ import annotations

__all__ = (
    'CaptchaDialog',
)

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...models import DeferredCallable
from ...models import DistributedCallable
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app


class CaptchaDialog(QWidget):
    """A :py:class:`CaptchaDialog` which signs in to the ChatGPT Client."""

    def __init__(self) -> None:
        """Create a new :py:class:`CaptchaDialog`."""
        super().__init__(None)

        app().client.authenticator.captchaEncountered.connect(DistributedCallable((
            DeferredCallable(self.show),
            self._set_image
        )))

        self._init_ui()

    def _init_ui(self) -> None:
        self.captcha_input = QLineEdit(self)
        self.captcha_view = QGraphicsView(QGraphicsScene(), self)

        init_objects({
            self: {
                'size': {'fixed': (400, 400)},
                'windowFlags': Qt.WindowType.Dialog,
                'windowModality': Qt.WindowModality.ApplicationModal,
                'windowIcon': app().icon_store['captcha'],
            },

            self.captcha_input: {
                'font': QFont('Söhne', 20),
                'alignment': Qt.AlignmentFlag.AlignCenter,
                'returnPressed': self._enter_captcha,
            },
        })

        app().init_translations({
            self.setWindowTitle: 'gui.captcha_dialog.title',
            self.captcha_input.setPlaceholderText: 'gui.captcha_dialog.captcha_placeholder',
        })

        init_layouts({
            # Main layout
            QVBoxLayout(self): {
                'items': (self.captcha_view, self.captcha_input)
            }
        })

    def _enter_captcha(self) -> None:
        # Do nothing if no answer yet
        if not (text := self.captcha_input.text()):
            return

        # Send captcha to Authenticator
        app().client.authenticator.solveCaptcha.emit(text)
        self.captcha_input.clear()
        self.close()

    def _set_image(self, image: QImage) -> None:
        self.captcha_view.scene().clear()
        self.captcha_view.scene().addPixmap(image)
