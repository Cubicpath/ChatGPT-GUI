###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Package-related utility functions."""
from __future__ import annotations

__all__ = (
    'current_requirement_licenses',
    'current_requirement_names',
    'current_requirement_versions',
    'has_package',
)


def current_requirement_licenses(
        package: str, recursive: bool = False, include_extras: bool = False
) -> dict[str, list[tuple[str, str]]]:
    """Return the current licenses for the requirements of the given package.

    :param package: Package name to search.
    :param recursive: Whether to get the requirements of the requirements of the given package.
    :param include_extras: Whether to include packages installed with extras.
    :return: dict mapping a package name to a list of license title and content pairs.
    """
    from importlib.metadata import metadata
    from pathlib import Path
    from pkg_resources import Distribution
    from pkg_resources import DistributionNotFound
    from pkg_resources import get_distribution

    result: dict[str, list[tuple[str, str]]] = {}
    for requirement in ([package] + current_requirement_names(package, recursive, include_extras)):
        try:
            dist: Distribution = get_distribution(requirement)
        except DistributionNotFound:
            continue

        name: str = dist.project_name.replace('-', '_')
        licenses: list[tuple[str, str]] = []

        # Find the distribution's information directory
        info_path = Path(dist.location) / f'{name}-{dist.version}.dist-info'
        if not info_path.is_dir():
            if (egg_path := info_path.with_name(f'{name}.egg-info')).is_dir():
                info_path = egg_path

        # Find the license file(s)
        license_files: list[Path] = [
            item for item in info_path.iterdir() if (
                item.is_file() and any(keyword in item.name.lower() for keyword in
                                       ('license', 'licence', 'copying', 'copyright', 'notice', 'author'))
            )
        ]

        # If the distribution has no 'License' field, get the distribution's Trove classifier
        if not (dist_license := metadata(name).get('License')):  # type: ignore
            for classifier in metadata(name).get_all('Classifier'):
                if classifier.startswith('License'):
                    # Ex: 'License :: OSI Approved :: MIT License'
                    dist_license = classifier.split('::')[-1].strip()
                    break

        # If there are multiple license/notice files, the title contains the filename
        for file in license_files:
            license_name: str = dist_license if len(license_files) == 1 else f'{dist_license} - {file.name}'
            licenses.append((license_name, file.read_text(encoding='utf8')))

        result[name] = licenses

    return result


def current_requirement_names(package: str, recursive: bool = False, include_extras: bool = False) -> list[str]:
    """Return the current requirement names for the given package.

    :param package: Package name to search.
    :param recursive: Whether to get the requirements of the requirements of the given package.
    :param include_extras: Whether to include packages installed with extras.
    :return: list of package names.
    """
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import requires

    req_names: set[str] = set()
    try:
        # Get the requirements for the given package, translating None to an empty tuple to allow iteration
        requirements: list[str] = requires(package) or []
    except PackageNotFoundError:
        # If the package is not installed, return an empty list
        return []

    for requirement in requirements:
        if not include_extras and '; extra' in requirement:
            continue

        # Don't include testing extras
        testing_extras = {'dev', 'develop', 'development', 'test', 'testing'}
        if include_extras and requirement.split('extra ==')[-1].strip().strip('"') in testing_extras:
            continue

        # Get the package name from the requirement
        # If no version identifier, assume the requirement string is the package name
        name: str = requirement
        has_version: bool = False
        split_pos: int = 0
        for split_pos, char in enumerate(requirement):
            if not char.isalnum() and char not in ('-', '_'):
                has_version = True
                break

        if has_version:
            name = requirement[:split_pos]

        req_names.add(name)
        if recursive:
            req_names.update(current_requirement_names(name, recursive, include_extras))

    return sorted(req_names, key=str.lower)


def current_requirement_versions(package: str, recursive: bool = False, include_extras: bool = False) -> dict[str, str]:
    """Return the current versions of the installed requirements for the given package.

    :param package: Package name to search.
    :param recursive: Whether to get the requirements of the requirements of the given package.
    :param include_extras: Whether to include packages installed with extras.
    :return: dict mapping package names to their version string.
    """
    from importlib.metadata import version

    return {name: version(name) for
            name in current_requirement_names(package, recursive, include_extras)
            if has_package(name)}


def has_package(package: str) -> bool:
    """Check if the given package is available.

    :param package: Package name to search; hyphen-insensitive.
    :return: Whether the given package name is installed to the current environment.
    """
    from pkg_resources import WorkingSet
    package = package.replace('-', '_')

    return any(
        package == pkg.project_name.replace('-', '_')
        for pkg in WorkingSet()
    )
