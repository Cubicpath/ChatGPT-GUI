###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Neutral namespace for constants. Meant to be star imported."""
from __future__ import annotations

__all__ = (
    'BYTE_UNITS',
    'CG_CACHE_PATH',
    'CG_CONFIG_PATH',
    'CG_PACKAGE_NAME',
    'CG_RESOURCE_PATH',
    'CG_SESSION_PATH',
    'CG_SESSION_PATH_OLD',
    'CG_URL_PATTERN',
    'CG_USER_AGENT',
    'MARKDOWN_IMG_LINK_PATTERN',
    'MARKDOWN_REF_LINK_PATTERN',
    'RFC_5646_PATTERN',
    'SUPPORTED_IMAGE_EXTENSIONS',
    'SUPPORTED_IMAGE_MIME_TYPES',
)

import re
from pathlib import Path
from typing import Final

# Mappings

BYTE_UNITS = {'Bytes': 1024**0, 'KiB': 1024**1, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
"""Mapping of byte units to their respective powers of 1024."""

# Sets

SUPPORTED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset({
    'bmp', 'cur', 'gif', 'icns', 'ico', 'jpeg', 'jpg', 'pbm', 'pgm', 'png',
    'ppm', 'svg', 'svgz', 'tga', 'tif', 'tiff', 'wbmp', 'webp', 'xbm', 'xpm'
})
"""Set containing all image file extensions supported by application."""

SUPPORTED_IMAGE_MIME_TYPES: Final[frozenset[str]] = frozenset({
    'image/bmp', 'image/gif', 'image/jpeg', 'image/png', 'image/svg+xml', 'image/svg+xml-compressed',
    'image/tiff', 'image/vnd.microsoft.icon', 'image/vnd.wap.wbmp', 'image/webp', 'image/x-icns',
    'image/x-portable-bitmap', 'image/x-portable-graymap', 'image/x-portable-pixmap', 'image/x-tga',
    'image/x-xbitmap', 'image/x-xpixmap'
})
"""Set containing all image mime types supported by application."""

# Strings

CG_PACKAGE_NAME: Final[str] = __package__.split('.', maxsplit=1)[0]
"""The base package name for this application, for use in sub-packages."""

CG_USER_AGENT: Final[str] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' \
                            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
"""User agent used when communicating with ChatGPT"""

# Paths

CG_CACHE_PATH: Final[Path] = Path.home() / '.cache/chatgpt_gui'
"""Directory containing cached API results."""

CG_CONFIG_PATH: Final[Path] = Path.home() / '.config/chatgpt_gui'
"""Directory containing user configuration data."""

CG_RESOURCE_PATH: Final[Path] = Path(__file__).parent / 'resources'
"""Directory containing application resources."""

CG_SESSION_PATH: Final[Path] = CG_CONFIG_PATH / '.session.json'
"""File containing session information."""

CG_SESSION_PATH_OLD: Final[Path] = CG_CONFIG_PATH / '.session'
"""File containing ONLY session token. Deprecated."""

# Patterns

CG_URL_PATTERN: Final[re.Pattern] = re.compile(
    r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|'
    r'[a-z0-9.\-]+[.][a-z]{2,}/)(?:[^\s()<>{}\[\]]+|'
    r'\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|'
    r'\(\S+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|'
    r'\(\S+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|'
    r'(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.][a-z]{2,}\b/?(?!@))')
"""Regex pattern for finding URLs.
Derived from https://gist.github.com/gruber/8891611.
"""

MARKDOWN_IMG_LINK_PATTERN: Final[re.Pattern] = re.compile(
    r'\[!\s*(?P<alt>\[[^\t\n\r()\[\]]*])\s*'
    r'(?P<image>\([\S ]+\))]\s*'
    r'(?P<target>[\[(][^\t\n\r()\[\]]*[)\]])')
"""Regex pattern for finding image links."""

MARKDOWN_REF_LINK_PATTERN: Final[re.Pattern] = re.compile(
    r'\[(?P<label>[^\[\]]+)] *: *'
    r'(?P<url>(?:(?:[a-zA-Z]+)?://)?'
    r'\w+(?:\.\w+)*(?::\d{1,5})?'
    r'(?:/[^\s()]*)?(?:\?(?:\w+=\w+&?)+)?)'
    r'(?: \"(?P<description>[^\"\t\n\r]*)\")?')
"""Regex pattern for finding markdown labels."""

RFC_5646_PATTERN: Final[re.Pattern] = re.compile(
    r'^(?=[a-z])(?:(?P<language>(?P<primary>[a-z]{2,3})(?:-(?P<extlang>[a-z]{3}))?)?'
    r'(?:-(?P<script>[a-z]{4}))?'
    r'(?:-(?P<region>[a-z]{2}|\d{3}))?'
    r'(?:-(?P<variants>(?:(?<![a-z\d])(?:[a-z\d]{5,8}|\d[a-z\d]{3})-?)+(?<!-)))?'
    r'(?:-(?P<extensions>(?:(?<![a-z\d])[a-wy-z\d]-[a-z\d]{2,8}-?)+(?<!-)))?)?'
    r'(?:-?(?<![a-z\d])(?P<private>x-(?:(?<![a-z\d])[a-z\d]{1,8}-?)+(?<!-)))?$',
    flags=re.IGNORECASE | re.ASCII)
"""Regex pattern for validating a language tag (langtag). Follows https://datatracker.ietf.org/doc/html/rfc5646

Uniqueness of variant subtags and extension singletons must be done outside of this pattern.

The language subtag is the primary subtag with the optional extlang subtag appended.

Most langtags are formatted as {language}-{REGION}.
Example langtags that follow RFC 5646::

    - "en" represents English ('en') with no region identifier.
    - "es-ES" represents Spanish ('es') as used in Spain ('ES').
    - "de-AT" represents German ('de') as used in Austria ('AT').
    - "sr-Latn" represents Serbian written using the Latin script.
    - "sr-Latn-RS" represents Serbian ('sr') written using Latin script ('Latn') as used in Serbia ('RS').
    - "es-419" represents Spanish ('es') appropriate to the UN-defined Latin America and Caribbean region ('419').
    - "sl-nedis" represents the Natisone or Nadiza dialect of Slovenian.
    - "de-CH-1996" represents German as used in Switzerland and as written using the spelling
            reform beginning in the year 1996 C.E.
    - en-a-bbb-x-a-ccc
    - x-private-tag-example
"""
