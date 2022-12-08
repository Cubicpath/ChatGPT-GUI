###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Account menu implementation."""
from __future__ import annotations

__all__ = (
    'AccountContextMenu',
    'confirm_sign_out',
)

from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...utils import add_menu_items
from ...utils import init_objects
from ..aliases import app
from ..aliases import tr


def confirm_sign_out() -> None:
    """Confirm user intention and sign out.

    :raises ValueError: If user is None.
    """
    if (user := app().client.user) is None:
        raise ValueError('Cannot sign out from a null User.')

    confirmation: bool = app().show_dialog(
        'questions.sign_out', None,
        buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        default_button=QMessageBox.StandardButton.Cancel,
        description_args=(user.email,)
    ).role == QMessageBox.ButtonRole.YesRole

    if confirmation:
        del app().client.session_token


class AccountContextMenu(QMenu):
    """Context menu that manages the logged in account."""

    def __init__(self, parent) -> None:
        """Create a new :py:class:`AccountContextMenu`."""
        super().__init__(parent)

        init_objects({
            (sign_in := QAction(self)): {
                'disabled': app().client.user is not None,
                'text': tr('gui.menus.account.sign_in'),
                'triggered': app().windows['sign_in'].show
            },

            (sign_out := QAction(self)): {
                'disabled': app().client.user is None,
                'text': tr('gui.menus.account.sign_out'),
                'triggered': confirm_sign_out
            },
        })

        add_menu_items(self, [
            'Sign In', sign_in,
            'Sign Out', sign_out
        ])
