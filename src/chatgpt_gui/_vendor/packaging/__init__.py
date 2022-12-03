###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""``packaging`` package stripped out and modified for version.py."""

__all__ = (
    'BaseVersion',
    'InvalidVersion',
    'LegacyVersion',
    'parse_version',
    'Version',
    'VERSION_PATTERN',
)

from .version import BaseVersion
from .version import InvalidVersion
from .version import LegacyVersion
from .version import parse as parse_version
from .version import Version
from .version import VERSION_PATTERN
