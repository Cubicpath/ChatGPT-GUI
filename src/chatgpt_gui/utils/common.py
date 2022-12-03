###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Common utility functions. These may be used in other utility modules."""
from __future__ import annotations

__all__ = (
    'bit_rep',
    'dump_data',
    'format_tb',
    'get_parent_doc',
    'get_weakref_object',
    'quote_str',
    'return_arg',
    'unique_values',
)

from collections.abc import Iterable
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType
from typing import TypeVar
from weakref import ProxyType

_PT = TypeVar('_PT')


def bit_rep(__bool: bool, /) -> str:
    """Return a string representing the bit value of a boolean."""
    return str(int(__bool))


def dump_data(path: Path | str, data: bytes | dict | str, encoding: str | None = None) -> None:
    """Dump data to path as a file."""
    import json
    import os

    default_encoding = 'utf8'
    path = Path(path)
    if not path.parent.exists():
        os.makedirs(path.parent)

    if isinstance(data, str):
        # Write strings at text files
        path.write_text(data, encoding=encoding or default_encoding)
    elif isinstance(data, bytes):
        # Decode bytes if provided with encoding, else write as data
        if encoding is not None:
            data = data.decode(encoding=encoding)
            path.write_text(data, encoding=encoding)
        else:
            path.write_bytes(data)
    elif isinstance(data, dict):
        # Write dictionaries as json files
        with path.open(mode='w', encoding=encoding or default_encoding) as file:
            json.dump(data, file, indent=2)


def format_tb(tb: TracebackType | None) -> str:
    """Format a traceback with linebreaks."""
    import traceback

    if tb is None:
        return ''

    return '\n'.join(traceback.format_tb(tb))


def get_parent_doc(__type: type, /) -> str | None:
    """Get the nearest parent documentation using the given :py:class:`type`'s mro.

    :return The closest docstring for an object's class, None if not found.
    """
    doc = None
    for parent in __type.__mro__:
        if doc := parent.__doc__:
            break
    return doc


def get_weakref_object(ref: ProxyType[_PT]) -> _PT:
    """Get the internal object of a weakref proxy."""
    import ctypes

    # Parse the proxy repr for the internal address
    addr_pos: int = repr(ref).rindex('0x')
    addr_str: str = repr(ref)[addr_pos:].strip(' ._<>')

    # Cast address into an object
    obj_val: _PT = ctypes.cast(int(addr_str, base=16), ctypes.py_object).value

    return obj_val


def quote_str(__str: str, /) -> str:
    """Encapsulate a string in double-quotes."""
    return f'"{__str}"'


def return_arg(__arg: _PT, /) -> _PT:
    """Return the singular positional argument unchanged."""
    return __arg


def unique_values(data: Iterable) -> set:
    """Recursively get all values in any Iterables. For Mappings, ignore keys and only remember values.

    :return Set containing all unique non-iterable values.
    """
    new: set = set()
    if isinstance(data, Mapping):
        # Loop through Mapping values
        for value in data.values():
            new.update(unique_values(value))
    elif isinstance(data, Iterable) and not isinstance(data, str):
        # Loop through Iterable values
        for value in data:
            new.update(unique_values(value))
    else:
        # Finally, get value
        new.add(data)
    return new
