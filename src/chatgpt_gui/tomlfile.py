###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Module used for TOML configurations."""
from __future__ import annotations

__all__ = (
    'CommentValue',
    'PathTomlDecoder',
    'PathTomlEncoder',
    'TomlFile',
    'TomlEvents',
    'TomlValue',
)

import warnings
from collections.abc import Callable
from collections.abc import MutableMapping
from pathlib import Path
from pathlib import PurePath
from typing import Any
from typing import Final
from typing import TypeAlias
from typing import TypeVar

import toml
from toml.decoder import CommentValue as _CommentValue

from .events import Event
from .events import EventBus

_COMMENT_PREFIX: Final[str] = '# '
_SPECIAL_PATH_PREFIX: Final[str] = '$PATH$|'

TomlValue: TypeAlias = dict[str, 'TomlValue'] | list['TomlValue'] | float | int | str | bool | PurePath
"""Represents a possible TOML value, with :py:class:`dict` being a Table, and :py:class:`list` being an Array."""


_TT = TypeVar('_TT', bound=TomlValue)  # Bound to TomlValue.


class _MetaCommentValue(type):
    """Overrides instance checks so that :py:class:`_CommentValue` is accepted as a :py:class:`CommentValue`."""

    def __instancecheck__(cls, instance: Any) -> bool:
        return isinstance(instance, _CommentValue)


class CommentValue(_CommentValue, metaclass=_MetaCommentValue):
    """Properly typed version of :py:class:`_CommentValue`."""

    def __init__(self, val: TomlValue, comment: str | None = None,
                 new_line: bool = False, _dict_type: type[MutableMapping] = dict) -> None:
        """Properly annotates types for :py:class:`_CommentValue`."""
        comment = f'{_COMMENT_PREFIX}{comment}' if comment is not None else ''
        separator: str = '\n' if new_line else ' '
        super().__init__(val, comment, new_line, _dict_type)

        self.val: TomlValue = val
        self.comment: str = separator + comment
        self._dict: type[MutableMapping] = _dict_type

    def __getitem__(self, key: str) -> TomlValue:
        """Proxy for :py:class:`MutableMapping`.__getitem__ if ``self.val`` is a :py:class:`MutableMapping`.

        :raises TypeError: If self.val is not a MutableMapping.
        """
        if not isinstance(self.val, MutableMapping):
            raise TypeError(f'Cannot access item for non-{self._dict} value.')
        return self.val[key]

    def __setitem__(self, key: str, value: TomlValue):
        """Proxy for :py:class:`MutableMapping`.__setitem__ if ``self.val`` is a :py:class:`MutableMapping`.

        :raises TypeError: If self.val is not a MutableMapping.
        """
        if not isinstance(self.val, MutableMapping):
            raise TypeError(f'Cannot assign item for non-{self._dict} value.')
        self.val[key] = value

    @classmethod
    def from_comment_val(cls, _comment_val: _CommentValue) -> CommentValue:
        """Make a :py:class:`CommentValue` from a :py:class:`_CommentValue`."""
        return cls(_comment_val.val, _comment_val.comment)

    def dump(self, dump_value_func: Callable[[TomlValue], str]) -> str:
        """Dump :py:class:`CommentValue` into a str."""
        ret_str: str = dump_value_func(self.val)
        if isinstance(self.val, self._dict):
            return self.comment + '\n' + str(ret_str)
        return str(ret_str) + self.comment


class TomlEvents:
    """Namespace for all events relating to :py:class:`TomlFile` objects."""

    class TomlEvent(Event):
        """Generic event for TomlFiles."""

        __slots__ = ('toml_file',)

        def __init__(self, toml_file: TomlFile) -> None:
            """Create a new :py:class:`TomlEvents.TomlEvent` event with the given file."""
            self.toml_file = toml_file

    class File(TomlEvent):
        """Accessing a File on disk."""

        __slots__ = ('path',)

        def __init__(self, toml_file: TomlFile, path: Path) -> None:
            """Create a new :py:class:`TomlEvents.File` event with the given file and path."""
            super().__init__(toml_file=toml_file)
            self.path = path

    class Import(File):
        """Loading a TomlFile."""

        __slots__ = ()

    class Export(File):
        """Exporting a TomlFile to disk."""

        __slots__ = ()

    class KeyAccess(TomlEvent):
        """A key's value is accessed."""

        __slots__ = ('key',)

        def __init__(self, toml_file: TomlFile, key: str) -> None:
            """Create a new :py:class:`TomlEvents.KeyAccess` event with the given file and key."""
            super().__init__(toml_file=toml_file)
            self.key: str = key

    class Get(KeyAccess):
        """Value is given."""

        __slots__ = ('value',)

        def __init__(self, toml_file: TomlFile, key: str, value: TomlValue) -> None:
            """Create a new :py:class:`TomlEvents.Get` event with the given file, key, and value."""
            super().__init__(toml_file=toml_file, key=key)
            self.value = value

    class Set(KeyAccess):
        """Value is set."""

        __slots__ = ('old', 'new')

        def __init__(self, toml_file: TomlFile, key: str, old: TomlValue | None, new: TomlValue) -> None:
            """Create a new :py:class:`TomlEvents.Set` event with the given file, key, old value, and new value."""
            super().__init__(toml_file=toml_file, key=key)
            self.old: TomlValue | None = old
            self.new: TomlValue = new

    class Fail(TomlEvent):
        """General Failure."""

        __slots__ = ('failure',)

        def __init__(self, toml_file: TomlFile, failure: str) -> None:
            """Create a new :py:class:`TomlEvents.Fail` event with the given file and failure value."""
            super().__init__(toml_file=toml_file)
            self.failure = failure


class PathTomlDecoder(toml.TomlPreserveCommentDecoder):
    """Inherits the effects of :py:class:`toml.TomlPreserveCommentEncoder`.

    With native support for pathlib :py:class:`Path` values; not abandoning the TOML specification.
    """

    def load_value(self, v: str, strictly_valid: bool = True) -> tuple[Any, str]:
        """Load the given string value into its decoded type.

        If the value is a string and starts with the SPECIAL_PATH_PREFIX,
        load the value enclosed in quotes as a :py:class:`Path`.
        """
        if v[1:].startswith(_SPECIAL_PATH_PREFIX):
            v_path = Path(v[1:].removeprefix(_SPECIAL_PATH_PREFIX)[:-1])
            return v_path, 'path'
        return super().load_value(v=v, strictly_valid=strictly_valid)


class PathTomlEncoder(toml.TomlEncoder):
    """Combines both the effects of :py:class:`toml.TomlPreserveCommentEncoder` and :py:class:`toml.TomlPathlibEncoder`.

    Has native support for pathlib :py:class:`PurePath`; not abandoning the TOML specification.
    """

    def __init__(self, _dict=dict, preserve=False) -> None:
        """Map extra ``dump_funcs`` for :py:class:`CommentValue` and :py:class:`PurePath`."""
        super().__init__(_dict, preserve)
        self.dump_funcs[_CommentValue] = lambda comment_val: comment_val.dump(self.dump_value)
        self.dump_funcs[CommentValue] = lambda comment_val: comment_val.dump(self.dump_value)
        self.dump_funcs[PurePath] = self._dump_pathlib_path

    @staticmethod
    def _dump_pathlib_path(v: PurePath) -> str:
        """Translate :py:class:`PurePath` to string and dump."""
        # noinspection PyProtectedMember
        return toml.encoder._dump_str(str(v))  # type: ignore

    def dump_value(self, v: TomlValue) -> str:
        """Support :py:class:`Path` decoding by prefixing a :py:class:`PurePath` string with a special marker."""
        if isinstance(v, PurePath):
            if isinstance(v, Path):
                v = v.resolve()
            v = f'{_SPECIAL_PATH_PREFIX}{v}'
        return super().dump_value(v=v)


class TomlFile:
    """Object that manages the getting and setting of TOML configurations.

    Houses an :py:class:`EventBus` that allows you to subscribe Callables to changes in configuration.
    """

    def __init__(self, path: Path | str, default: dict[str, TomlValue | _CommentValue] | None = None) -> None:
        """Initialize a :py:class:`TomlFile` object.

        :param path: Path to the TOML file.
        :param default: Default values for the TOML file.
        """
        self._path: Path = Path(path)
        self._data: dict[str, TomlValue | _CommentValue] = {} if default is None else default
        self.event_bus: EventBus[TomlEvents.TomlEvent] = EventBus()
        if not self.reload():
            warnings.warn(f'Could not load TOML file {self.path} on initialization.')

    def __getitem__(self, key: str) -> TomlValue:
        """Get the associated TOML value from the key."""
        return self.get(key)

    def __setitem__(self, key: str, value: TomlValue) -> None:
        """Set the key's associated TOML value."""
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        """Delete the key and it's associated TOML value."""
        del self._data[key]

    def _search_scope(self, path: str, mode: str) -> tuple[dict[str, TomlValue | _CommentValue], str]:
        """Search data for the given path to the value, and if found, return the scope and the key that path belongs to.

        :param path: Path to search data for.
        :param mode: Mode that determines which exceptions to raise.
        :return: Tuple containing the scope where the value is found, and the value key to access.
        :raises KeyError: If mode is 'set' and path is a table OR if mode is 'get' and path doesn't exist.
        :raises ValueError: If path is an empty string.
        """
        if not path:
            raise ValueError('Path cannot be an empty string.')

        key: str = path
        scope: dict[str, TomlValue | _CommentValue] = self._data
        paths: list[str] = path.split('/')

        if len(paths) > 1:
            for i, key in enumerate(paths):
                if key:
                    val: TomlValue | _CommentValue | None = scope.get(key)
                    if i == len(paths) - 1:
                        if mode == 'set' and isinstance(scope.get(key), dict):
                            raise KeyError(f'Cannot reassign Table "{".".join(paths[:i])}" to variable.')
                        if mode == 'get' and key not in scope:
                            raise KeyError(f'Key "{key}" not in Table "{".".join(paths[:i]) or "/"}".')

                    elif isinstance(val, dict):
                        scope = val  # type: ignore
                        continue

        return scope, key

    @property
    def path(self) -> Path:
        """:return: Current OS path that TomlFile with save and reload from."""
        return self._path

    @path.setter
    def path(self, value: Path | str) -> None:
        """Set the path to the TOML file to save and reload from.

        Translates string paths to pathlib Paths.
        """
        self._path = Path(value)

    def get(self, key: str) -> TomlValue:
        """Get a value from the key path. Searches with each '/' defining a new table to check.

        :param key: Key to get value from.
        :return: Value of key.
        :raises KeyError: If key doesn't exist.
        :raises ValueError: If key is an empty string.
        """
        scope, path = self._search_scope(key, mode='get')
        val: TomlValue | _CommentValue = scope[path]

        # Get value from _CommentValue
        if isinstance(val, _CommentValue):
            val = CommentValue.from_comment_val(val).val

        self.event_bus << TomlEvents.Get(self, key, val)

        return val

    def set(self, key: str, value: TomlValue, comment: str | None = None) -> None:
        """Set a key at path. Searches with each '/' defining a new table to check.

        :param key: Key to set.
        :param value: Value to set key as.
        :param comment: Append an optional comment to the value.
        :raises KeyError: If key evaluates to a table.
        :raises ValueError: If key is an empty string.
        """
        scope, path = self._search_scope(key, 'set')
        prev_val: TomlValue | _CommentValue | None = scope.get(path)
        new_val: TomlValue | _CommentValue = value

        if comment is not None:
            new_val = CommentValue(value, comment)

        # Preserve comments, or edit them if comment argument was filled
        elif isinstance(prev_val, _CommentValue):
            if comment is None:
                comment = prev_val.comment.lstrip().removeprefix(_COMMENT_PREFIX)

            new_val = CommentValue(value, comment, new_line=prev_val.comment.startswith('\n'))

        scope[path] = new_val

        self.event_bus << TomlEvents.Set(
            self, key,
            old=prev_val.val if isinstance(prev_val, _CommentValue) else prev_val,
            new=value
        )

    def save(self) -> bool:
        """Save current settings to self.path.

        :return: True if successful, otherwise False.
        """
        return self.export_to(self.path)

    def reload(self) -> bool:
        """Reset settings to settings stored in self.path.

        :return: True if successful, otherwise False.
        """
        return self.import_from(self.path, update=True)

    def export_to(self, path: Path | str) -> bool:
        """Export internal dictionary as a TOML file to path.

        :param path: Path to export TOML file to.
        :return: True if successful, otherwise False.
        """
        path = Path(path)  # Make sure path is of type Path
        if path.parent.is_dir():
            with path.open(mode='w', encoding='utf8') as file:
                toml.dump(self._data, file, encoder=PathTomlEncoder())

            self.event_bus << TomlEvents.Export(self, path)
            return True

        self.event_bus << TomlEvents.Fail(self, 'export')
        return False

    def import_from(self, path: Path | str, update: bool = False) -> bool:
        """Import TOML file from path to internal dictionary.

        :param path: Path to import TOML file from.
        :param update: If True, will update existing keys with new values, instead of replacing the internal dictionary.
        :return: True if successful, otherwise False.
        """
        path = Path(path)  # Make sure path is of type Path
        if path.is_file():
            try:
                with path.open(mode='r', encoding='utf8') as file:
                    toml_data = toml.load(file, decoder=PathTomlDecoder())
                    if update:
                        self._data |= toml_data
                    else:
                        self._data = toml_data

            except (LookupError, OSError, toml.TomlDecodeError):
                pass  # Pass to end of function, to fail.

            else:
                self.event_bus.fire(TomlEvents.Import(self, path))
                return True

        # If failed:
        self.event_bus << TomlEvents.Fail(self, 'import')
        return False
