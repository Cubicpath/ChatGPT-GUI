###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Custom :py:class:`Exception`'s and excepthook implementation."""
from __future__ import annotations

__all__ = (
    'ExceptHookCallable',
    'ExceptionEvent',
    'ExceptionHook',
)

import sys
from collections.abc import Callable
from types import TracebackType
from typing import TypeAlias

from .events import Event
from .events import EventBus

ExceptHookCallable: TypeAlias = Callable[[type[BaseException], BaseException, TracebackType], None]


class ExceptionEvent(Event):
    """Event fired when an exception is caught by an :py:class:`ExceptionHook`."""

    __slots__ = ('exception', 'traceback')

    def __init__(self, exception: BaseException, traceback: TracebackType) -> None:
        """Create a new :py:class:`ExceptionEvent` event with the given exception and its associated traceback."""
        self.exception: BaseException = exception
        self.traceback: TracebackType = traceback


class ExceptionHook:
    """Object that intercepts :py:class:`Exception`'s and handles them."""

    def __init__(self, bus_id: str | None = 'exceptions'):
        """Initialize the :py:class:`ExceptionHook` for use in a context manager."""
        self.__old_hook: ExceptHookCallable = sys.excepthook
        self.event_bus: EventBus = EventBus(bus_id)

    def __call__(self, type_: type[BaseException], exception: BaseException, traceback: TracebackType) -> None:
        """When an exception is raised."""
        # Don't handle BaseExceptions
        if not issubclass(type_, Exception):
            return self.old_hook(type_, exception, traceback)

        self.event_bus << ExceptionEvent(exception, traceback)

    def __repr__(self) -> str:
        """Representation of the :py:class:`ExceptionHook` with the old hook."""
        return f'<{type(self).__name__} ({self.old_hook=})>'

    def __enter__(self) -> None:
        """Temporary extend current exception hook."""
        sys.excepthook = self

    def __exit__(self, *_) -> None:
        """Reset current exception hook to the original one."""
        sys.excepthook = self.old_hook
        del EventBus['exceptions']

    @property
    def old_hook(self) -> ExceptHookCallable:
        """Return the original exception hook."""
        return self.__old_hook
