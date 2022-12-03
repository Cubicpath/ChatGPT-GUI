###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ExceptionLogger implementation."""
from __future__ import annotations

__all__ = (
    'ExceptionLogger',
    'LoggedException',
)

from datetime import datetime
from types import TracebackType
from typing import NamedTuple

from PySide6.QtWidgets import *

from ...events import EventBus
from ...exception_hook import ExceptionEvent
from ..aliases import tr


class ExceptionLogger(QPushButton):
    """A :py:class:`QPushButton` that logs exceptions to the event bus."""

    level_icon_list: list = [
        QStyle.StandardPixmap.SP_MessageBoxInformation,  # 0, Not a concern
        QStyle.StandardPixmap.SP_MessageBoxWarning,      # 1, Warning
        QStyle.StandardPixmap.SP_MessageBoxCritical      # 2, Error
    ]

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the ExceptionLogger."""
        from ..windows import ExceptionReporter

        super().__init__(*args, **kwargs)
        EventBus['exceptions'].subscribe(self.on_exception, ExceptionEvent)

        self.label: QLabel = QLabel(self)
        self.exception_log: list[LoggedException] = []
        self.reporter: ExceptionReporter = ExceptionReporter(self)
        self.severity = 0

        self.reporter.setMinimumWidth(300)

    def clear_exceptions(self) -> None:
        """Clear the exception log and disable the button."""
        self.exception_log.clear()
        self.severity = 0
        self.setText('')
        self.label.setText(tr('gui.status.default'))

    def remove_exception(self, index: int) -> None:
        """Remove an exception from the log and update the current severity."""
        if self.exception_log:
            self.exception_log.pop(index)

        if not self.exception_log:
            self.clear_exceptions()
        else:
            logged = len(self.exception_log)
            self.setText(f'({logged})' if logged < 10 else '(9+)')
            self.severity = self.exception_log[0].severity

    def on_exception(self, event: ExceptionEvent) -> None:
        """Update the exception log and change set the max level."""
        level = 1 if isinstance(event.exception, Warning) and self.severity < 1 else 2

        self.severity = max(self.severity, level)

        self.exception_log.append(LoggedException(level, event.exception, event.traceback, datetime.now()))
        self.sort_exceptions()

        logged = len(self.exception_log)
        self.setText(f'({logged})' if logged < 10 else '(9+)')

    def sort_exceptions(self) -> None:
        """Sort the exception log by severity."""
        if self.exception_log:
            self.exception_log = list(reversed(sorted(self.exception_log, key=lambda x: x.severity)))
            self.severity = self.exception_log[0].severity
        else:
            self.severity = 0

    @property
    def severity(self) -> int:
        """Get the max level of the exception log."""
        return self._severity

    @severity.setter
    def severity(self, value: int) -> None:
        """Set the max level of the exception log and update the icon."""
        self._severity = value
        self.setIcon(self.style().standardIcon(self.level_icon_list[self.severity]))
        self.reporter.setWindowIcon(self.icon())


class LoggedException(NamedTuple):
    """Container for a logged exception.

    Includes the severity of the exception, the exception itself, an optional traceback, and a timestamp.
    """

    severity: int = 0
    exception: BaseException | None = None
    traceback: TracebackType | None = None
    timestamp: datetime | None = None
