###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""An independent script to upgrade the version of a given package, then launch it."""

import subprocess
import sys
from pathlib import Path


def main(package_to_install: str, module_to_run: str | None = None) -> None:
    """Script entry point. if __name__ == '__main__'."""
    python = Path(sys.executable)

    # Ensure that pip is ran under windowless, so it doesn't install GUI scripts directing to "pythonww.exe".
    # This is due to pip appending a "w" to it's own executable path.
    pip_python = python.with_stem(python.stem.removesuffix('w'))

    subprocess.run(  # nosec B603:subprocess_without_shell_equals_true
        (pip_python, '-m', 'pip', 'install', '--upgrade', package_to_install),
        capture_output=True, text=True, check=True
    )

    if module_to_run is not None:
        subprocess.run(  # nosec B603:subprocess_without_shell_equals_true
            (python, '-m', module_to_run),
            check=False
        )


if __name__ == '__main__':
    main(*sys.argv[1:3])
