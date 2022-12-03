###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""PasteLineEdit implementation."""
from __future__ import annotations

__all__ = (
    'PasteLineEdit',
)

from collections.abc import Callable

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class PasteLineEdit(QLineEdit):
    """A :py:class:`QLineEdit` with an added paste listener."""

    pasted = Signal()

    def __init__(self, *args, pasted: Callable[[], None] | None = None, **kwargs) -> None:
        """Initialize the ``pasted`` keyword argument onto the ``self.pasted`` signal."""
        super().__init__(*args, **kwargs)
        if pasted is not None:
            self.pasted.connect(pasted)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Call self.pasted on paste."""
        super().keyPressEvent(event)
        if event.matches(QKeySequence.StandardKey.Paste):
            self.pasted.emit()
        event.accept()
