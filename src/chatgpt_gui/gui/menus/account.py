###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Account menu implementation."""
from __future__ import annotations

__all__ = (
    'AccountContextMenu',
)

from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...models import DeferredCallable
from ...utils import add_menu_items
from ...utils import init_objects
from ..aliases import app
from ..aliases import tr


class AccountContextMenu(QMenu):
    """Context menu that manages the logged in account."""

    def __init__(self, parent) -> None:
        """Create a new :py:class:`AccountContextMenu`."""
        super().__init__(parent)

        init_objects({
            (login_to := QAction(self)): {
                'text': tr('gui.menus.account.login_to'),
                'triggered': DeferredCallable(
                    app().show_dialog, 'test'
                )
            },
        })

        add_menu_items(self, [
            'Login to...', login_to
        ])
