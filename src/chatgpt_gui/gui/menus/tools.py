###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Tools menu implementation."""
from __future__ import annotations

__all__ = (
    'create_app_shortcut',
    'ToolsContextMenu',
)

import sys
from pathlib import Path

from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...constants import *
from ...utils import add_menu_items
from ...utils import init_objects
from ...utils import create_shortcut
from ..aliases import app
from ..aliases import tr


def create_app_shortcut() -> None:
    """Create shortcut for starting program."""
    exec_path = Path(sys.executable)

    desktop_button = QPushButton(tr('gui.menus.tools.create_shortcut.only_desktop'))
    start_menu_button = QPushButton(tr('gui.menus.tools.create_shortcut.only_start_menu'))
    both_button = QPushButton(tr('gui.menus.tools.create_shortcut.both'))

    # Show dialog, return early if user presses cancel
    if (response := app().show_dialog(
        'questions.create_shortcut', None, (
            (desktop_button, QMessageBox.ButtonRole.AcceptRole),
            (start_menu_button, QMessageBox.ButtonRole.AcceptRole),
            (both_button, QMessageBox.ButtonRole.AcceptRole),
            QMessageBox.StandardButton.Cancel
        ), default_button=QMessageBox.StandardButton.Cancel
    )).role == QMessageBox.ButtonRole.RejectRole:
        return

    # If response is affirmative, mark which shortcuts to create
    do_desktop = response.button in {desktop_button, both_button}
    do_start_menu = response.button in {start_menu_button, both_button}

    # Get the windowless Python executable name (append w)
    name = exec_path.stem
    shortcut_path = exec_path.with_stem(name if name.endswith('w') else name + 'w')

    # Create shortcut to launch this package, with proper kwargs
    create_shortcut(target=shortcut_path, arguments=f'-m {CG_PACKAGE_NAME}',
                    name=tr('app.name'), description=tr('app.description'),
                    icon=CG_RESOURCE_PATH / 'icons/openai.ico', terminal=False,
                    desktop=do_desktop, start_menu=do_start_menu)


class ToolsContextMenu(QMenu):
    """Context menu for tools."""

    def __init__(self, parent) -> None:
        """Create a new :py:class:`ToolsContextMenu`."""
        super().__init__(parent)

        # noinspection PyUnresolvedReferences
        init_objects({
            (shortcut_tool := QAction(self)): {
                'text': tr('gui.menus.tools.create_shortcut'),
                'icon': self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon),
                'triggered': create_app_shortcut
            },

            (exception_reporter := QAction(self)): {
                'text': tr('gui.menus.tools.exception_reporter'),
                'icon': app().windows['app'].exception_reporter.logger.icon(),  # type: ignore
                'triggered': app().windows['app'].exception_reporter.show       # type: ignore
            }
        })

        add_menu_items(self, [
            'Tools', shortcut_tool, exception_reporter
        ])
