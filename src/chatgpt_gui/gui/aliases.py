###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Convenience alias functions."""
from __future__ import annotations

__all__ = (
    'app',
    'tr',
)

from typing import Any

from .app import GetterApp


def app() -> GetterApp:
    """Return :py:class:`GetterApp`.instance()."""
    return GetterApp.instance()


def tr(key: str, *args: Any, **kwargs: Any) -> str:
    """Alias for app().translator().

    :param key: Translation keys to translate.
    :param args: Arguments to format key with.
    :keyword default: Default value to return if key is not found.
    :return: Translated text.
    """
    return app().translator(key, *args, **kwargs)
