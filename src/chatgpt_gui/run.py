###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Initialize values and runs the application. :py:func:`main` acts as an entry-point."""
from __future__ import annotations

__all__ = (
    'main',
)

import sys

from ._version import __version__
from .exception_hook import ExceptionHook
from .gui import GetterApp
from .utils import patch_windows_taskbar_icon


def main(*args: str) -> int:
    """Run the program. GUI script entrypoint.

    Args are passed to a QApplication instance.
    """
    patch_windows_taskbar_icon(f'cubicpath.{__package__}.app.{__version__}')

    # ExceptionHook is required for subscribing to ExceptionEvents
    with ExceptionHook():
        GetterApp.create(*args)

        app: GetterApp = GetterApp.instance()
        app.windows['app'].show()
        return app.exec()


if __name__ == '__main__':
    main(*sys.argv)
