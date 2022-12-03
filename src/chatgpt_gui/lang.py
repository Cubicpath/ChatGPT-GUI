###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Module containing code related to translation and language files."""
from __future__ import annotations

__all__ = (
    'default_language_file',
    'format_value',
    'Language',
    'to_lang',
    'Translator',
)

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import Final

from .constants import *

_POS_PARAM_REF: Final[re.Pattern] = re.compile(r'{([1-9]\d*|0)}')
"""Pattern for finding positional parameter references."""

_KEY_REF: Final[re.Pattern] = re.compile(r'{[\w\-.]*}')
"""Pattern for finding lang key references."""

_LANG_PATH: Final[Path] = CG_RESOURCE_PATH / 'lang'
"""Directory containing language JSON data."""


def default_language_file() -> Path:
    """Return the first path found that has ".default" in its extension.

    ex: en.default.json

    :raises FileNotFoundError: If .default file is not found.
    """
    default_lang_file: Path | None = None
    for lang_file in _LANG_PATH.iterdir():
        if '.default' in lang_file.suffixes:
            default_lang_file = lang_file
            break

    if default_lang_file is None:
        raise FileNotFoundError('No file with the suffix of .default.json found.')

    return default_lang_file


def format_value(
        value: str,
        *args: Any,
        _language: Language | None = None,
        _key_eval: bool = True
) -> str:
    r"""Format a str with positional arguments.

    You can use {0} notation to refer to a specific positional argument.
    If the notation chars are replaced with the argument, you can no longer use it as a normal positional argument.

    JSON strings ex::

        {
            "a": "{0} is the same as {0} using only one argument.",
            "b": "{0} %s will not work and require 2 arguments",
            "c": "%s {0} is the same as above, where \"%s\" is now the 2nd argument since the 1st is used by \"{0}\""
        }
    """
    list_args: list[Any] = list(args)
    replaced: set[str] = set()

    for matches in _POS_PARAM_REF.finditer(value):
        match: str = matches[0]
        arg_val: Any = args[int(match.strip('{}'))]
        if match not in replaced:
            replaced.add(match)
            value = value.replace(match, arg_val)
            list_args.remove(arg_val)

    value = value % tuple(list_args)

    if _key_eval and _language is not None:
        replaced.clear()
        for _ in range(50):
            # Loop if a match is found, to recursively get translation key values.
            # Limit of 50 to prevent an infinite loop.

            found: bool = False
            for rec_matches in _KEY_REF.finditer(value):
                found = True
                if (rec_match := rec_matches[0]) not in replaced:
                    replaced.add(rec_match)
                    value = value.replace(rec_match, _language.get_raw(rec_match.strip('{}')))

            if not found:
                # End loop if no inner translation keys are found.
                break

    return value


def matched_subtags(tag: str) -> dict[str, str]:
    """Match all subtags in a valid language tag and returns a dictionary representation.

    :param tag: Language tag which follows RFC 5646.
    :return: Dictionary containing subtags and their values.
    :raises ValueError: If ``tag`` is not a valid language tag.
    """
    if (match := RFC_5646_PATTERN.match(tag)) is not None:
        return match.groupdict()
    raise ValueError(f'"{tag}" is not a valid language tag (RFC 5646).')


def to_lang(language: str | Language) -> Language:
    """Assert that a given value is a :py:class:`Language`."""
    if not isinstance(language, Language):
        language = str(language)  # Stringify non-language object

    if isinstance(language, str):
        language = Language.from_tag(language)
    return language


class Language:
    """Object containing language data. Retrieves stored data with associated RFC 5646 language tags."""

    def __init__(
            self,
            primary: str,
            region: str | None = None,
            _selected_file: Path | None = None,
            **kwargs: str | None
    ) -> None:
        """Build a new Language object using given sub-tags.

        For more information on RFC 5646, visit https://datatracker.ietf.org/doc/html/rfc5646

        :param primary: The first part of the language code. i.e. [en]-US | Section 2.2.1
        :param region: The (commonly) second part of the language code. i.e. en-[US] | Section 2.2.4

        :keyword extlang: Extension to primary subtag | Section 2.2.2
        :keyword script: Script used to write the language | Section 2.2.3
        :keyword variants: A variant of the given language subtag | Section 2.2.5
        :keyword extensions: Extension to the given language, prefixed with a singleton | Section 2.2.6
        :keyword private: Any subtag that is not publicly defined | Section 2.2.7
        """
        subtags: dict[str, str | None] = {'primary': primary, 'region': region}
        subtags.update(kwargs)

        self._data: dict[str, str] = {}
        self.tag: str = Language.build_tag(subtags)
        self.subtags: dict[str, str] = matched_subtags(self.tag)

        if _selected_file is None:
            _selected_file = self.closest_file()

        if _selected_file is not None:
            # Read the language file corresponding to this Language's tags.
            file_data: dict[str, Any] = json.loads(_selected_file.read_text(encoding='utf8'))

            # Read the parent language file if it exists.
            if (parent_lang := file_data['meta'].get('inherits_from')) is not None:
                self._data |= Language.from_tag(parent_lang).data

            # Overwrite inherited keys.
            self._data |= file_data['keys']

    def __repr__(self) -> str:
        """Representation of the :py:class:`Language` with its tag and number of loaded language keys."""
        return f'<Language data for {self.tag} ({len(self.data)} keys)>'

    def __getitem__(self, key: str) -> str:
        """Get the raw value of the given key (No formatting)."""
        return self.get_raw(key)

    @classmethod
    def from_tag(cls, tag: str) -> Language:
        """Build a :py:class:`Language` object using a plain string tag.

        Breaks tag into sub-tags and verifies compliance with RFC 5646.

        :raises ValueError: If tag is not a valid language tag.
        """
        return cls(**matched_subtags(tag))

    @classmethod
    def from_path(cls, path: Path | str) -> Language:
        """Build a :py:class:`Language` object using a plain string tag.

        Breaks tag into sub-tags and verifies compliance with RFC 5646.

        :raises ValueError: If tag from the path's filename is not a valid language tag.
        """
        path = Path(path)
        tag: str = Path(path).stem.split('.')[0].replace('_', '-')
        return cls(**matched_subtags(tag), _selected_file=path)

    @staticmethod
    def build_tag(tag_dict: dict[str, str | None]) -> str:
        """Build tag from a tag dictionary.

        :param tag_dict: Dictionary obtained from RFC_5646_PATTERN.match(tag).groupdict()
        :return: String representation of tag with correct case formatting.

        :raises ValueError: If a given subtag is invalid.
        """
        (primary, extlang, script, region, variants, extensions, private) = (
            tag_dict.pop('primary', None),
            tag_dict.pop('extlang', None),
            tag_dict.pop('script', None),
            tag_dict.pop('region', None),
            tag_dict.pop('variants', None),
            tag_dict.pop('extensions', None),
            tag_dict.pop('private', None),
        )

        checked: set[str] = set()
        subtags: list[str] = []
        err: Exception | None = None

        if primary is None and private is None:
            err = ValueError('The primary and/or private subtag must be filled out.')

        if primary is not None:
            subtags.append(primary.lower())

        if extlang is not None:
            subtags.append(extlang.lower())

        if script is not None:
            subtags.append(script.title())

        if region is not None:
            subtags.append(region.upper())

        if variants is not None:
            for subtag in variants.split('-'):
                # RFC 5646 section 2.2.5.5
                if (variant := subtag.lower()) in checked:
                    err = ValueError(f'Variant subtag "{subtag}" is repeated.')

                checked.add(variant)
                subtags.append(variant)
            checked.clear()

        if extensions is not None:
            for i, subtag in enumerate(extensions.split('-')):
                if not i % 2:
                    # RFC 5646 section 2.2.6.3
                    if (singleton := subtag.lower()) in checked:
                        err = ValueError(f'Singleton subtag "{subtag}" is repeated.')

                    checked.add(singleton)
                subtags.append(subtag.lower())
            checked.clear()

        if private is not None:
            for subtag in private.split('-'):
                subtags.append(subtag.lower())

        tag: str = '-'.join(subtags)

        if err is not None:
            raise ValueError(str(err)[:-1] + f' in language tag "{tag}".') from err

        return tag

    @property
    def data(self) -> dict[str, Any]:
        """Return a copy of the internal key dictionary."""
        return self._data.copy()

    def closest_file(self) -> Path | None:
        """Find the most relevant file in the ``_LANG_DIR`` to represent this :py:class:`Language`'s tag.

        The primary language subtag MUST match for a lang file to be considered. ex::

            "en-Latn-US-1994" would regress to en_us.json, as they both share their primary and region subtags.
            "es-US" would NOT regress to en_us.json, as they do not share their primary subtags.

        """
        most_relevant: tuple[Path | None, int] = (None, 0)

        for lang_file in _LANG_PATH.iterdir():
            if lang_file.suffix == '.json':
                file_tag: str = lang_file.stem.split('.')[0].replace('_', '-').lower()

                # For exact match
                if self.tag.lower() == file_tag:
                    most_relevant = (lang_file, 1000)
                    break

                file_subtags: dict[str, str] = matched_subtags(file_tag)

                # Count how close our tag is to this file's tag
                intersection = {a: b for ((a, b), (c, d))
                                in zip(self.subtags.items(), file_subtags.items())
                                if a == c and b is not None and d is not None and b.lower() == d.lower()}

                # Ensure that the primary language subtag is the same
                if intersection.get('primary') is not None:
                    relevance = len(intersection)
                else:
                    relevance = 0

                if relevance > most_relevant[1]:
                    most_relevant = (lang_file, relevance)

        return most_relevant[0]

    def get(self, key: str, *args: Any, default: str | None = None, key_eval: bool = True) -> str:
        """Get a translation key and format with the given arguments if required.

        :param key: Key to get in JSON data.
        :param args: Formatting arguments; packed into tuple and used with str modulus.
        :param default: Default string if key doesn't exist. (Is not formatted)
        :param key_eval: If False, don't recursively evaluate translation keys.
        """
        # Default value is key if not overridden
        default = default if default is not None else key

        if (result := self._data.get(key, default)) is not default:
            return format_value(result, *args, _language=self, _key_eval=key_eval)

        # Dont format default value
        quote = '"'
        for arg in (f'%{str(arg) if not isinstance(arg, str) else quote + arg + quote}%' for arg in args):
            result += arg
        return result

    def get_raw(self, key: str) -> str:
        """Get raw result, no formatting or defaults.

        :raises KeyError: If key is not in JSON data.
        """
        return self._data[key]


class Translator:
    """Simple class meant to abstract key translation into a function-like state.

    Usage::
        translate = Translator('en-US')
        translate('a.translation.key') -> american value
        translate.language = 'de-GER'
        translate('a.translation.key') -> german value
    """

    def __init__(self, language: Language | str | None = None) -> None:
        """Create a :py:class:`Translator` for the given :py:class:`Language`.

        If not langauge is supplied, it defaults to the default_language_file.

        :param language: Language to use for translator.
        """
        if language is not None:
            self._language = to_lang(language)
        else:
            self._language = Language.from_path(default_language_file())

    def __bool__(self) -> bool:
        """Return whether the :py:class:`Translator` is available."""
        return True

    def __call__(self, key: str, *args: Any, **kwargs) -> str:
        """Syntax sugar for get_translation."""
        return self.get_translation(key, *args, **kwargs)

    def __repr__(self) -> str:
        """Representation of the :py:class:`Translator` with its tag and number of loaded language keys."""
        language = self.language
        return f'<Translator {language=}>'

    @property
    def language(self) -> Language:
        """Return current :py:class:`Language` for this translator."""
        return self._language

    @language.setter
    def language(self, value: Language | str) -> None:
        self._language = to_lang(value)

    def get_translation(self, key: str, *args: Any, **kwargs) -> str:
        """Get a translation key's value for the current language."""
        return self.language.get(key, *args, **kwargs)

    @contextmanager
    def as_language(self, language: Language | str) -> Iterator[None]:
        """Temporarily translate for a specific language using a context manager."""
        # __enter__
        old_lang = self._language
        self.language = language
        yield

        # __exit__
        self._language = old_lang
