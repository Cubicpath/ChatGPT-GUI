###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ExceptionReporter implementation."""
from __future__ import annotations

__all__ = (
    'ExceptionReporter',
)

from getpass import getuser

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ..._version import __version__
from ...events import EventBus
from ...exception_hook import ExceptionEvent
from ...models import DeferredCallable
from ...models import DistributedCallable
from ...utils import delete_layout_widgets
from ...utils import encode_url_params
from ...utils import format_tb
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app
from ..aliases import tr
from ..widgets import ExceptionLogger
from ..widgets import ExternalTextBrowser


class ExceptionReporter(QWidget):
    """A :py:class:`QWidget` that displays logged exceptions and their traceback."""

    def __init__(self, logger: ExceptionLogger) -> None:
        """Create a new :py:class:`ExceptionReporter` and initialize UI."""
        super().__init__()
        EventBus['exceptions'].subscribe(DeferredCallable(self.reload_exceptions), ExceptionEvent)

        self.selected: int = 0
        self.logger: ExceptionLogger = logger
        self.setWindowTitle(tr('gui.exception_reporter.title'))
        self.setWindowIcon(self.logger.icon())
        self.resize(QSize(750, 400))
        self._init_ui()

    def _init_ui(self) -> None:
        self.left_panel = QFrame(self)
        self.right_panel = QFrame(self)

        self.trace_back_viewer = ExternalTextBrowser(self)
        self.clear_button = QPushButton(self.right_panel)
        self.report_button = QPushButton(self.right_panel)

        # Define the scroll area/widget for the left panel
        self.scroll_area = QScrollArea(self)
        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setLayout(QVBoxLayout())
        self.scroll_widget.layout().setAlignment(Qt.AlignmentFlag.AlignTop)

        init_objects({
            self.scroll_area: {
                'widget': self.scroll_widget,
                'widgetResizable': True
            },

            self.left_panel: {'layout': QVBoxLayout()},
            self.right_panel: {'layout': QVBoxLayout()},
            (left_label := QLabel(self.left_panel)): {},
            (right_label := QLabel(self.right_panel)): {},

            (clear_all_button := QPushButton(self.left_panel)): {
                'clicked': self.clear_all_exceptions
            },

            self.trace_back_viewer: {
                'disabled': True,
                'font': QFont('consolas', 10),
                'lineWrapMode': QTextEdit.LineWrapMode.NoWrap
            },

            self.clear_button: {
                'disabled': True,
                'size': {'maximum': (self.report_button.width() // 1, None)},
                'clicked': self.clear_current_exception
            },

            self.report_button: {
                'disabled': True,
                'clicked': self.report_current_exception
            }
        })

        app().init_translations({
            self.setWindowTitle: 'gui.exception_reporter.title',

            # Labels
            left_label.setText: 'gui.exception_reporter.exception_list',
            right_label.setText: 'gui.exception_reporter.traceback_label',

            # Buttons
            clear_all_button.setText: 'gui.exception_reporter.clear_all',
            self.clear_button.setText: 'gui.exception_reporter.clear',
            self.report_button.setText: 'gui.exception_reporter.report'
        })

        init_layouts({
            # Left frame layout
            self.left_panel.layout(): {
                'items': [left_label, self.scroll_area, clear_all_button]
            },

            # Right frame layouts
            (buttons := QHBoxLayout()): {
                'items': [self.report_button, self.clear_button]
            },
            self.right_panel.layout(): {
                'items': [right_label, self.trace_back_viewer, buttons]
            },

            # Main layout
            QHBoxLayout(self): {
                'items': [self.left_panel, self.right_panel]
            }
        })

        self.left_panel.setLayout(QVBoxLayout())
        self.right_panel.setLayout(QVBoxLayout())

    def report_current_exception(self) -> None:
        """Report the current exception to the exception logger."""
        selected = self.logger.exception_log[self.selected]

        exc_name: str = type(selected.exception).__name__
        exc_msg: str = str(selected.exception).rstrip('.')
        exc_tb: str = format_tb(selected.traceback).strip().replace(getuser(), '%USERNAME%')

        base: str = 'https://github.com/Cubicpath/ChatGPT-GUI/issues/new'
        params: dict[str, str] = {
            'template': 'bug-report.yaml',
            'assignees': 'Cubicpath',
            'labels': 'bug',
            'projects': 'Cubicpath/ChatGPT-GUI/2',
            'title': f'[Bug]: ({exc_name}) {exc_msg}',
            'version': f'v{__version__}',
            'logs': f'{exc_name}: {exc_msg}\n\n{exc_tb}'
        }
        QDesktopServices.openUrl(QUrl(f'{base}?{encode_url_params(params)}'))

    def disable_exception_widgets(self) -> None:
        """Disables the widgets on the right pane."""
        self.trace_back_viewer.clear()
        self.trace_back_viewer.setDisabled(True)
        self.report_button.setDisabled(True)
        self.clear_button.setDisabled(True)

    def clear_all_exceptions(self) -> None:
        """Clear all exceptions from the list."""
        self.logger.clear_exceptions()
        self.disable_exception_widgets()
        delete_layout_widgets(self.scroll_widget.layout())

    def clear_current_exception(self) -> None:
        """Clear the currently selected exception and removes it from the log."""
        if (item := self.scroll_widget.layout().takeAt(self.selected)) is not None:
            self.logger.remove_exception(self.selected)
            item.widget().deleteLater()
        self.reload_exceptions()
        self.disable_exception_widgets()

    def reload_exceptions(self) -> None:
        """Load the exceptions from the logger."""
        delete_layout_widgets(self.scroll_widget.layout())
        for i, error in enumerate(self.logger.exception_log):
            button = QPushButton(f'{type(error.exception).__name__}: {error.exception}', self.scroll_widget)
            clicked = button.clicked  # pyright: ignore[reportGeneralTypeIssues]
            clicked.connect(DeferredCallable(setattr, self, 'selected', i))
            clicked.connect(DistributedCallable((
                self.clear_button.setDisabled,
                self.report_button.setDisabled,
                self.trace_back_viewer.setDisabled
            ), False))
            clicked.connect(DeferredCallable(self.trace_back_viewer.setText, DeferredCallable(
                tr, 'gui.exception_reporter.traceback_view',
                type(error.exception).__name__, error.exception, format_tb(error.traceback),
                key_eval=False
            )))

            button.setStyleSheet('text-align:left;')
            button.setMaximumWidth((self.size().width() // 3) - 50)

            self.scroll_widget.layout().addWidget(button)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Resizes the left panel to better fit the window."""
        super().resizeEvent(event)
        self.left_panel.setMaximumWidth(event.size().width() // 3)
        for i in range(self.scroll_widget.layout().count()):
            self.scroll_widget.layout().itemAt(i).widget().setMaximumWidth((event.size().width() // 3) - 50)
        event.accept()
