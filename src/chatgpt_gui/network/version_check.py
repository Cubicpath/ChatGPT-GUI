###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Version checking and validation."""
from __future__ import annotations

__all__ = (
    'get_version',
    'is_greater_version',
    'VersionChecker',
)

from datetime import datetime
from importlib.metadata import version

from PySide6.QtCore import *

from .._vendor.packaging import BaseVersion
from .._vendor.packaging import LegacyVersion
from .._vendor.packaging import parse_version
from .._vendor.packaging import Version
from .._version import __version__
from ..constants import *
from ..utils.package import has_package
from .manager import NetworkSession
from .manager import Response


def get_version(package_name: str) -> LegacyVersion | Version | None:
    """Return the :py:class:`Version` of the given package if it is installed. Else return None."""
    if has_package(package_name):
        return parse_version(version(package_name))


def is_greater_version(version1: BaseVersion | str, version2: BaseVersion | str) -> bool:
    """Return whether ``version1`` is greater than ``version2``."""
    if not isinstance(version1, BaseVersion):
        version1 = parse_version(version1)
    if not isinstance(version2, BaseVersion):
        version2 = parse_version(version2)

    return version1 > version2


class VersionChecker(QObject):
    """Checks for the latest versions of packages."""

    checked = Signal(str)
    newerVersion = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Create a new :py:class:`VersionChecker` and initialize its :py:class:`NetworkSession`."""
        super().__init__(parent)

        self.session: NetworkSession = NetworkSession(self)

    def check_version(self, package_name: str = CG_PACKAGE_NAME) -> None:
        """Check the latest version of the given package on PyPI.

        If the latest version is greater than the current version,
        emit the ``newerVersion`` signal with the given name and the latest version as arguments.

        Emit the ``checked`` signal after a successful call.

        :param package_name: The package to look up on PyPI.
        """
        def handle_reply(reply: Response):
            # Sort versions on date released
            versions: list[str] = sorted(
                releases := reply.json['releases'],
                key=lambda v: datetime.strptime(releases[v][0]['upload_time_iso_8601'], '%Y-%m-%dT%H:%M:%S.%fZ')
            )

            # Get local version of given package. Use __version__ attribute for own package.
            local_version: BaseVersion | str
            if package_name != CG_PACKAGE_NAME:
                if (ver := get_version(package_name)) is None:
                    return
                local_version = ver
            else:
                local_version = __version__

            # Get the latest version and compare to current version. Emit newerVersion if greater.
            latest: str = versions[-1]
            if is_greater_version(latest, local_version):
                self.newerVersion.emit(package_name, latest)
            self.checked.emit(package_name)

        self.session.get(f'https://pypi.org/pypi/{package_name.replace("_", "-").strip()}/json', finished=handle_reply)
