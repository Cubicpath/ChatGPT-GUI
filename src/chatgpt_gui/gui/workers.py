###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Implementations for worker-thread runnables."""
from __future__ import annotations

__all__ = ()

from collections.abc import Callable

from PySide6.QtCore import *
from shiboken6 import Shiboken


class _SignalHolder(QObject):
    exceptionRaised = Signal(Exception)
    valueReturned = Signal(object)


class _Worker(QRunnable):
    _signal_holder: type[_SignalHolder] = _SignalHolder

    def __init__(self, **kwargs: Callable | Slot) -> None:
        super().__init__()
        self.signals = self._signal_holder()

        # Connect signals from keyword arguments
        for kw, val in kwargs.items():
            if hasattr(self.signals, kw) and isinstance((signal := getattr(self.signals, kw)), SignalInstance):
                signal.connect(val)
            else:
                raise TypeError(f'"{kw}" is not a valid kwarg or signal name.')

    # pylint: disable=no-self-use
    def _dummy_method(self) -> None:
        return

    def _run(self) -> None:
        raise NotImplementedError

    # pylint: disable=broad-except
    @Slot()
    def run(self) -> None:
        """Ran by the :py:class:`QThreadPool`.

        Sends non-``None`` return values through the ``valueReturned`` signal.
            - If you need to return ``None``, I suggest creating a separate object to represent it.

        Sends any uncaught :py:class:`Exception`'s through the ``exceptionRaised`` signal.

        :raises RuntimeError: If worker started before application instance is defined.
        """
        if (app := QCoreApplication.instance()) is None:
            raise RuntimeError('Worker started before application instance is defined.')

        # No idea how, but this fixes application deadlock cause by RecursiveSearch (issue #31)
        app.aboutToQuit.connect(  # pyright: ignore[reportGeneralTypeIssues]
            self._dummy_method, Qt.ConnectionType.BlockingQueuedConnection
        )

        try:
            # Emit non-None return values through the `valueReturned` signal.
            if (ret_val := self._run()) is not None:
                self.signals.valueReturned.emit(ret_val)

        except Exception as e:
            # This occurs when the application is exiting and an internal C++ object is being read after it is deleted.
            # So, return quietly and allow the process to exit with no errors.
            if not Shiboken.isValid(self.signals):
                return

            self.signals.exceptionRaised.emit(e)

        # Disconnect deadlock safeguard if successful to avoid possible leak
        app.aboutToQuit.disconnect(self._dummy_method)  # pyright: ignore[reportGeneralTypeIssues]

        # Delete if not deleted
        if Shiboken.isValid(self.signals):
            self.signals.deleteLater()
