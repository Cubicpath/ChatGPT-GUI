# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
#
# https://github.com/pypa/packaging/blob/main/LICENSE
"""This file has been refurbished by Cubicpath@Github to follow modern typing and documentation practices."""
from __future__ import annotations

__all__ = (
    'Infinity',
    'InfinityType',
    'NegativeInfinity',
    'NegativeInfinityType',
)

from typing import Any


class InfinityType:
    def __repr__(self) -> str:
        return 'Infinity'

    def __hash__(self) -> int:
        return hash(repr(self))

    def __lt__(self, other: Any) -> bool:
        return False

    def __le__(self, other: Any) -> bool:
        return False

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__)

    def __ne__(self, other: Any) -> bool:
        return not isinstance(other, self.__class__)

    def __gt__(self, other: Any) -> bool:
        return True

    def __ge__(self, other: Any) -> bool:
        return True

    def __neg__(self) -> NegativeInfinityType:
        return NegativeInfinity


Infinity = InfinityType()


class NegativeInfinityType:
    def __repr__(self) -> str:
        return '-Infinity'

    def __hash__(self) -> int:
        return hash(repr(self))

    def __lt__(self, other: Any) -> bool:
        return True

    def __le__(self, other: Any) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__)

    def __ne__(self, other: Any) -> bool:
        return not isinstance(other, self.__class__)

    def __gt__(self, other: Any) -> bool:
        return False

    def __ge__(self, other: Any) -> bool:
        return False

    def __neg__(self) -> InfinityType:
        return Infinity


NegativeInfinity = NegativeInfinityType()
