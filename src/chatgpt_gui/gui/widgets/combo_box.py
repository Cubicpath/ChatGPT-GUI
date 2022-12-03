###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ComboBox implementations."""
from __future__ import annotations

__all__ = (
    'ComboBox',
    'HistoryComboBox',
    'TranslatableComboBox',
)

from collections.abc import Iterable
from collections.abc import Iterator

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...utils import init_objects
from ..aliases import tr
from .paste_line_edit import PasteLineEdit


class ComboBox(QComboBox):
    """Iterable :py:class:`QComboBox`."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize :py:class:`ComboBox` values."""
        super().__init__(*args, **kwargs)
        self._iter_index = -1

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """Iterate over items and their associated data."""
        self._iter_index = -1
        return self

    def __next__(self) -> tuple[str, str]:
        """Return the next item and its data.

        :return: display text and key, packaged into a tuple.
        :raises StopIteration: When iteration index reaches the last item.
        """
        self._iter_index += 1

        if self._iter_index <= self.count() - 1:
            return self.itemText(self._iter_index), self.itemData(self._iter_index)

        raise StopIteration

    def addItems(self, texts: Iterable[str], *args, **kwargs) -> None:
        """self.addItem for text in texts."""
        for text in texts:
            self.addItem(text, *args, **kwargs)


class HistoryComboBox(ComboBox):
    """Editable :py:class:`ComboBox` acting as a history wrapper over :py:class:`PasteLineEdit`.

    Has no duplicate values.
    """

    line_edit_class = PasteLineEdit

    def __init__(self, *args, **kwargs) -> None:
        """Initialize :py:class:`HistoryComboBox` values."""
        super().__init__(*args, **kwargs)

        init_objects({
            self: {
                'editable': True,
                'duplicatesEnabled': False,
                'lineEdit': self.line_edit_class(parent=self)
            }
        })

    # noinspection PyTypeChecker
    def addItem(self, text: str, *args, **kwargs) -> None:
        """Filter already-present strings from being added using addItem."""
        if (result := self.findText(text, Qt.MatchFlag.MatchFixedString)) != -1:
            self.removeItem(result)

        super().addItem(text, *args, **kwargs)


class TranslatableComboBox(ComboBox):
    """:py:class:`ComboBox` with translatable items."""

    def translate_items(self, *_) -> None:
        """Translate all items with their respective key."""
        items = tuple(key for _, key in self)
        self.clear()
        self.addItems(items)

    # noinspection PyTypeChecker
    def addItem(self, text: str, *args, **kwargs) -> None:
        """Translate strings from being added using addItem."""
        super().addItem(tr(text), *args, userData=text, **kwargs)
