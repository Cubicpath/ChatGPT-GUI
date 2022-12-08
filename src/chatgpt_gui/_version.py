###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Version information."""
# Store the version here so:
# 1) We don't load dependencies by storing it in __init__.py
# 2) We can load it in setup.cfg
# 3) We can import it into modules

__version_info__ = (0, 3, 0, 'final', 0)
"""Major, Minor, Micro, Release level, Serial in respective order."""


def _stringify(major: int, minor: int, micro: int = 0, releaselevel: str = 'final', serial: int = 0, **kwargs) -> str:
    """Stringifies a version number based on version info given. Follows :pep:`440`.

    Releaselevel is the status of the given version, NOT the project itself.
    All versions of an alpha or beta should be a 'final' releaselevel.

    Serial is only taken into account if releaselevel is not 'final' or 'release'.

    For developmental releases, post releases, and local release specifications, see
    https://www.python.org/dev/peps/pep-0440/#normalization

    | Ex: (2021, 9) -> 2021.9
    | Ex: (0, 3, 2, 'beta') -> 0.3.2b
    | Ex: (1, 0, 0, 'release') -> 1.0
    | Ex: (3, 10, 0, 'candidate', 0) -> 3.10rc
    | Ex: (3, 9, 1, 'alpha', 3) -> 3.9.2a3
    | Ex: (3, 9, 1, dev=2) -> 3.9.2.dev2
    | Ex: (3, 9, 2, 'preview', 3, post=0, post_implicit=True, dev=5) -> 3.9.2pre3-0.dev5
    | Ex: (1, 0, local='ubuntu', local_ver='2', local_ver_sep='-') -> 1.0+ubuntu-2

    :param major: First and most important version number.
    :param minor: Second and less important version number.
    :param micro: Last and least important version number.
    :param releaselevel: Status of current version.
    :param serial: Separate version number of an Alpha/Beta for an upcoming release version.
    :keyword local: Local release type, ex: 'ubuntu'
    :keyword local_ver: Local release version
    :keyword local_ver_sep: Local release seperator
    :keyword pre_sep: Pre-release seperator
    :keyword pre_ver_sep: Pre-release version seperator
    :keyword post: Post-release version
    :keyword post_spelling: How post is represented (post, rev, r)
    :keyword post_implicit: Post-release version
    :keyword post_sep: Post-release seperator
    :keyword post_ver_sep: Post-release version seperator
    :keyword dev: Developmental release version
    :keyword dev_sep: Developmental release seperator
    :keyword dev_post: Developmental Post-release version
    :keyword dev_post_sep: Developmental Post-release seperator
    :keyword dev_post_ver_sep: Developmental Post-release version seperator
    :return: String representation of version number.
    :raises TypeError: Version numbers are not integers.
    :raises ValueError: Version separators are not in the allowed chars.
    """
    (local, local_ver, local_ver_sep, pre_sep, pre_ver_sep,
     post, post_spelling, post_implicit, post_sep, post_ver_sep,
     dev, dev_sep, dev_post, dev_post_sep, dev_post_ver_sep) = (
        kwargs.pop('local', None),
        kwargs.pop('local_ver', 0),
        kwargs.pop('local_ver_sep', '.'),
        kwargs.pop('pre_sep', ''),
        kwargs.pop('pre_ver_sep', ''),
        kwargs.pop('post', None),
        kwargs.pop('post_spelling', 'post'),
        kwargs.pop('post_implicit', False),
        kwargs.pop('post_sep', ''),
        kwargs.pop('post_ver_sep', ''),
        kwargs.pop('dev', None),
        kwargs.pop('dev_sep', ''),
        kwargs.pop('dev_post', None),
        kwargs.pop('dev_post_sep', ''),
        kwargs.pop('dev_post_ver_sep', ''),
    )

    releaselevel = releaselevel.strip()
    separators: tuple[str, ...] = ('', '.', '-', '_')
    post_spellings: tuple[str, ...] = ('post', 'rev', 'r')
    release_levels: tuple[str, ...] = ('a', 'b', 'c', 'rc', 'pre', 'alpha', 'beta',
                                       'candidate', 'preview', 'final', 'release')

    for attr in ('major', 'minor', 'micro', 'local_ver', 'post', 'dev', 'dev_post'):
        if vars()[attr] is not None and not isinstance(vars()[attr], int):
            raise TypeError(f'Argument "{attr}" should be of type {int}')  # pragma: no cover
    if (local_ver_sep not in separators[1:] or False in (
            sep in separators for sep in (pre_sep, pre_ver_sep, post_sep, post_ver_sep,
                                          dev_sep, dev_post_sep, dev_post_ver_sep)
    )):
        raise ValueError(f'A separator given is not in allowed separators {separators}')
    if post_spelling not in post_spellings:
        raise ValueError(f'Post-release spelling not allowed as "{post_spelling}"')
    if releaselevel not in release_levels:
        raise ValueError(f'Release level "{releaselevel}" is not in known release levels')

    v_number: str = f'{major}.{minor}'
    v_number += f'.{micro}' if micro else ''

    if releaselevel and releaselevel not in ('final', 'release'):
        if releaselevel in {'candidate', 'c'}:
            releaselevel = 'rc'
        if releaselevel in {'alpha', 'beta'}:
            releaselevel = releaselevel[0]
        if releaselevel == 'preview':
            releaselevel = 'pre'
        v_number += pre_sep
        v_number += releaselevel if len(releaselevel) <= 3 else releaselevel[0]
        v_number += f'{pre_ver_sep}{serial}' if serial else ''

    if post is not None:
        sep = f'{post_sep}{post_spelling}' if not post_implicit else '-'
        v_number += f'{sep}{post_ver_sep if post else ""}{post if post or sep == "-" else ""}'

    if dev is not None:
        v_number += f'{dev_sep}dev{dev if dev else ""}'

    if dev_post is not None:
        sep = f'{dev_post_sep + post_spelling}' if not post_implicit else '-'
        v_number += f'{sep}{dev_post_ver_sep if dev_post else ""}{dev_post if dev_post or sep == "-" else ""}'

    if local is not None:
        v_number += f'+{local + local_ver_sep}{local_ver}'

    return v_number


__version__ = _stringify(*__version_info__)
"""String representation of version number."""
