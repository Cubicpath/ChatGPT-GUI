###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Main application window implementation."""
from __future__ import annotations

__all__ = (
    'AppWindow',
    'size_label_for',
)

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...constants import *
from ...events import EventBus
from ...exception_hook import ExceptionEvent
from ...models import DeferredCallable
from ...models import DistributedCallable
from ...models import Singleton
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app
from ..menus import HelpContextMenu
from ..menus import ToolsContextMenu
from ..widgets import HistoryComboBox
from ..widgets import ExceptionLogger
from ..widgets import ExternalTextBrowser
from .exception_reporter import ExceptionReporter


def size_label_for(num: int) -> str:
    """Return the best display unit to describe the given data's size.

    Ex: Bytes, KiB, MiB, GiB, TiB
    """
    display_unit = 'Bytes'
    for size_label, size in BYTE_UNITS.items():
        if num >= (size // 2):
            display_unit = size_label
        else:
            break
    return display_unit


class AppWindow(Singleton, QMainWindow):
    """Main window for the ChatGPT-GUI application."""

    _singleton_base_type = QMainWindow
    _singleton_check_ref = False
    shown_key_warning: bool = False

    def __init__(self, size: QSize) -> None:
        """Create the window for the application."""
        super().__init__()

        self.current_image: QPixmap | None = None
        self.detached: dict[str, QMainWindow | None] = {'media': None, 'text': None}
        self.resize(size)

        self.exception_reporter: ExceptionReporter
        self.input_field: HistoryComboBox
        self.media_frame: QFrame
        self.image_size_label: QLabel
        self.image_detach_button: QPushButton
        self.media_output: QGraphicsView
        self.text_frame: QFrame
        self.text_size_label: QLabel
        self.text_detach_button: QPushButton
        self.text_output: ExternalTextBrowser
        self.clear_picture: QPushButton
        self.copy_picture: QPushButton
        self.clear_text: QPushButton
        self.copy_text: QPushButton

        self._init_toolbar()
        self._init_ui()

    def _init_toolbar(self) -> None:
        """Initialize toolbar widgets."""
        from .settings import SettingsWindow

        def context_menu_handler(menu_class: type[QMenu]) -> None:
            """Create a new :py:class:`QMenu` and show it at the cursor's position.

            :raises TypeError: If menu_class is not an instance of QMenu.
            """
            if not issubclass(menu_class, QMenu):
                raise TypeError(f'{menu_class} is not a subclass of {QMenu}')

            menu: QMenu = menu_class(self)
            menu.exec(self.cursor().pos())
            menu.deleteLater()

        init_objects({
            (menu_bar := QToolBar(self)): {},

            (status_bar := QToolBar(self)): {
                'movable': False,
            },

            (settings := QAction(self)): {
                'menuRole': QAction.MenuRole.PreferencesRole,
                'triggered': DistributedCallable((
                    SettingsWindow.instance().show,            # pyright: ignore[reportGeneralTypeIssues]
                    SettingsWindow.instance().activateWindow,  # pyright: ignore[reportGeneralTypeIssues]
                    SettingsWindow.instance().raise_           # pyright: ignore[reportGeneralTypeIssues]
                ))
            },

            (tools := QAction(self)): {
                'menuRole': QAction.MenuRole.ApplicationSpecificRole,
                'triggered': DeferredCallable(context_menu_handler, ToolsContextMenu)
            },

            (help := QAction(self)): {
                'menuRole': QAction.MenuRole.AboutRole,
                'triggered': DeferredCallable(context_menu_handler, HelpContextMenu)
            },

            (logger := ExceptionLogger(self)): {
                'size': {'fixed': (None, 20)},
                'clicked': DistributedCallable((
                    logger.reporter.show,
                    logger.reporter.activateWindow,
                    logger.reporter.raise_
                ))
            }
        })

        app().init_translations({
            menu_bar.setWindowTitle: 'gui.menu_bar.title',
            status_bar.setWindowTitle: 'gui.status_bar.title',
            settings.setText: 'gui.menus.settings',
            tools.setText: 'gui.menus.tools',
            help.setText: 'gui.menus.help',
            logger.label.setText: 'gui.status.default'
        })

        self.exception_reporter = logger.reporter

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, menu_bar)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, status_bar)

        EventBus['exceptions'].subscribe(lambda e: logger.label.setText(f'{e.exception}...'), ExceptionEvent)
        for action in (settings, tools, help):
            menu_bar.addSeparator()
            menu_bar.addAction(action)

        status_bar.addWidget(logger)
        status_bar.addSeparator()
        status_bar.addWidget(logger.label)

    # noinspection PyTypeChecker
    def _init_ui(self) -> None:
        """Initialize the UI, including Layouts and widgets."""
        # Define widget attributes
        # Cannot be defined in init_objects() as walrus operators are not allowed for object attribute assignment.
        # This works in the standard AST, but is a seemingly arbitrary limitation set by the interpreter.
        # See:
        # https://stackoverflow.com/questions/64055314/why-cant-pythons-walrus-operator-be-used-to-set-instance-attributes#answer-66617839

        init_objects({})

        app().init_translations({})

        init_layouts({
            # Main layout
            (layout := QGridLayout()): {
                'items': []
            }
        })

        init_objects({
            (main_widget := QWidget()): {'layout': layout},

            self: {'centralWidget': main_widget}
        })

    # # # # # Events

    def show(self) -> None:
        """After window is displayed, show warnings if not already warned."""
        super().show()

        if app().first_launch:
            app().windows['readme_viewer'].show()
            app().show_dialog('information.first_launch', self)

        elif not self.shown_key_warning:
            app().show_dialog('warnings.empty_token', self)
            self.__class__.shown_key_warning = True

    def closeEvent(self, event: QCloseEvent) -> None:
        """Close all detached/children windows and quit application."""
        super().closeEvent(event)
        # Remember window size
        app().settings.reload()
        app().settings['gui/window/x_size'] = self.size().width()
        app().settings['gui/window/y_size'] = self.size().height()
        app().settings.save()

        app().quit()
        event.accept()
