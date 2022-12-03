###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""System utility functions."""
from __future__ import annotations

__all__ = (
    'create_shortcut',
    'get_desktop_path',
    'get_start_menu_path',
    'get_winreg_value',
    'hide_windows_file',
    'patch_windows_taskbar_icon',
)

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..constants import *
from .common import bit_rep
from .common import quote_str


def create_shortcut(target: Path, arguments: str | None = None,
                    name: str | None = None, description: str | None = None,
                    icon: Path | None = None, working_dir: Path | None = None,
                    desktop: bool = True, start_menu: bool = True,
                    version: str | None = None, terminal: bool = True) -> None:
    """Create a shortcut on the given path.

    Notes
        * start_menu is ignored on macOS
        * terminal is ignored by Windows
        * working_dir is Windows only
        * version is Linux only

    Linux and macOS implementations are heavily based on pyshortcuts.

    :param target: Target of the shortcut.
    :param arguments: Command line arguments to pass to the target.
    :param version: Version identifier of the target.
    :param terminal: Whether to open the target with a terminal.
    :param name: Name of the shortcut.
    :param description: Description of the shortcut.
    :param icon: Path to an icon to use for the shortcut.
    :param working_dir: Working directory to start in when executing the shortcut.
    :param desktop: Whether to create a desktop shortcut.
    :param start_menu: Whether to create a start menu shortcut.
    :raises ValueError: icon extension cannot be used as an icon for the given platform.
    """
    import shutil
    import subprocess
    import sys

    if not desktop and not start_menu:
        return

    target = target.resolve(True).absolute()
    name = 'Shortcut' if name is None else name
    working_dir = Path.home() if working_dir is None else working_dir

    PLATFORM_SHORTCUT_DATA: dict[str, dict[str, Any]] = {
        'darwin': {
            'shortcut_ext': '.app',
            'icon_exts': ('.icns',),
        },
        'linux': {
            'shortcut_ext': '.desktop',
            'icon_exts': ('.ico', '.svg', '.png'),
        },
        'win32': {
            'shortcut_ext': '.lnk',
            'icon_exts': ('.ico', '.exe'),
        }
    }

    if not (data := PLATFORM_SHORTCUT_DATA.get(sys.platform)):
        return

    if icon and icon.suffix not in data['icon_exts']:
        raise ValueError(f'Icon must be one of {data["icon_exts"]} for {sys.platform}')

    if (platform := sys.platform.lower()) == 'darwin':
        # macOS doesn't support start menu shortcuts, so return if not creating a desktop shortcut
        if not desktop:
            return

        # Create the desktop directory if it doesn't exist
        if (desktop_path := get_desktop_path()) is not None:
            if not desktop_path.is_dir():
                desktop_path.mkdir(parents=True)

            # Create the shortcut folders, replacing if it already exists
            dest = (desktop_path / name).with_suffix(data['shortcut_ext'])
            if dest.exists():
                shutil.rmtree(dest)

            dest.mkdir(parents=True)
            (dest / 'Contents').mkdir()
            (dest / 'Contents/MacOS').mkdir()
            (dest / 'Contents/Resources').mkdir()

            # Add macOS shortcut data
            with (dest / 'Contents/Info.plist').open('w', encoding='utf8') as plist:
                # noinspection HttpUrlsUsage
                plist.writelines([
                    '<?xml version="1.0" encoding="UTF-8"?>\n',
                    '<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"\n',
                    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n',
                    '<plist version="1.0">\n',
                    '  <dict>\n',
                    f'  <key>CFBundleGetInfoString</key> <string>{description or ""}</string>\n',
                    f'  <key>CFBundleName</key> <string>{name}</string>\n',
                    f'  <key>CFBundleExecutable</key> <string>{name}</string>\n',
                    f'  <key>CFBundleIconFile</key> <string>{name}</string>\n',
                    '  <key>CFBundlePackageType</key> <string>APPL</string>\n',
                    '  </dict>\n',
                    '</plist>\n',
                ])

            with (dest / f'Contents/MacOS/{name}').open('w', encoding='utf8') as shortcut_script:
                shortcut_script.writelines([
                    '#!/bin/bash\n',
                    # These exports are not used if the script is ran from the terminal
                    f'export SCRIPT={target}\n',
                ])
                if arguments is not None:
                    shortcut_script.write(f'export ARGS=\'{arguments}\'\n')

                if not terminal:
                    shortcut_script.write(f'$SCRIPT{" $ARGS" if arguments else ""}')
                else:
                    osa_script = f'{target} {arguments}'.replace(' ', '\\ ')
                    shortcut_script.writelines([
                        'osascript - e \'tell application "Terminal"\n',
                        f'do script "\'{osa_script}\'"\n',
                        'end tell\n',
                        '\'\n',
                    ])

                shortcut_script.write('\n')

            # Change permissions to allow execution
            (dest / f'Contents/MacOS/{name}').chmod(0o755)  # rwxr-xr-x

            # Add the icon
            if icon:
                shutil.copy(icon, (dest / f'Contents/Resources/{name}').with_suffix(icon.suffix))

    elif platform.startswith('linux'):
        entry_values: dict[str, object] = {
            'Encoding': 'UTF-8',
            'Version': version,
            'Type': 'Application',
            'Exec': f'{target} {arguments}',
            'Terminal': terminal,
            'Icon': icon,
            'Name': name,
            'Comment': description,
        }

        for (do, path) in (
                (desktop, get_desktop_path()),
                (start_menu, get_start_menu_path())
        ):
            if do:
                # Create the directory if it doesn't exist
                if not path.is_dir():
                    path.mkdir(parents=True)

                # Create the .desktop file
                dest = (path / name).with_suffix(data['shortcut_ext'])
                with dest.open('w', encoding='utf8') as shortcut_script:
                    shortcut_script.write('[Desktop Entry]\n')
                    shortcut_script.writelines([
                        f'{k}={v}\n' for k, v in entry_values.items() if v is not None
                    ])

                # Change permissions to allow execution
                dest.chmod(0o755)  # rwxr-xr-x

    elif platform == 'win32':
        arg_factories: dict[str, tuple[Any, Callable[[Any], str]]] = {
            'Target': (target, quote_str),
            'Arguments': (arguments, quote_str),
            'Name': (name, quote_str),
            'Description': (description, quote_str),
            'Icon': (icon, quote_str),
            'WorkingDirectory': (working_dir, quote_str),
            'Extension': (data['shortcut_ext'], quote_str),
            'Desktop': (desktop, bit_rep),
            'StartMenu': (start_menu, bit_rep)
        }

        abs_script_path: Path = (CG_RESOURCE_PATH / 'scripts/CreateShortcut.ps1').resolve(True).absolute()
        powershell_arguments = [
            'powershell.exe', '-ExecutionPolicy', 'Unrestricted', abs_script_path,
        ]

        # Append keyword arguments to the powershell script if the value is not None
        # Every argument is in the form of -<keyword>:<value> with value being
        # represented as a quoted string or raw integer.
        powershell_arguments.extend([
            f'-{key}:{factory(value)}' for (key, (value, factory)) in arg_factories.items() if value is not None
        ])

        # All user input is passed in as a controlled powershell.exe argument.
        subprocess.run(  # nosec B603:subprocess_without_shell_equals_true
            powershell_arguments, capture_output=True, text=True, check=True
        )


def get_desktop_path() -> Path:
    """Cross-platform utility to obtain the path to the desktop.

    This function is cached after the first call.

    * On Windows, this returns the path found in the registry, or
      the default ~/Desktop if the registry could not be read from.

    * On Linux and macOS, this returns the DESKTOP value in ~/.config/user-dirs.dirs file, or
      the default ~/Desktop.

    :return: Path to the user's desktop directory.
    :raises TypeError: If winreg value for Desktop shell folder is not a string/path.
    """
    import os
    import sys

    # Assume that once found, the desktop path does not change
    if hasattr(get_desktop_path, '__cached__'):
        return get_desktop_path.__cached__

    platform: str = sys.platform.lower()
    desktop: Path

    if platform == 'win32':
        shell_folder_key = r'HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
        desktop = Path.home() / 'Desktop'

        try:
            val = get_winreg_value(shell_folder_key, 'Desktop')
            if not isinstance(val, str):
                raise TypeError(f'Winreg value of {shell_folder_key}\\Desktop is not a string.')

            # Make sure the path is resolved
            desktop = Path(val).resolve(True).absolute()

        except (ImportError, OSError):
            pass  # Return the default windows path if the registry couldn't be read.

    else:  # Linux, Darwin
        home: Path = Path.home() or Path(os.environ['HOME'])
        desktop = home / 'Desktop'

        # If desktop is defined in user's config, use that
        dir_file: Path = home / '.config/user-dirs.dirs'
        if dir_file.is_file():
            with dir_file.open(mode='r', encoding='utf8') as f:
                text: list[str] = f.readlines()

            for line in text:
                # Read the DESKTOP variable's value and evaluate it
                if 'DESKTOP' in line:
                    line: str = line.replace('$HOME', str(home))[:-1]
                    config_val: str = line.split('=')[1].strip('\'\"')
                    desktop = Path(config_val).resolve(True).absolute()

    get_desktop_path.__cached__ = desktop
    return desktop


def get_start_menu_path() -> Path:
    """Cross-platform utility to obtain the path to the Start Menu or equivalent.

    This function is cached after the first call.

    * On Windows, this returns the main Start Menu folder, so it is
      recommended that you use the "Programs" sub-folder for adding shortcuts.

    * On Linux, this returns the ~/.local/share/applications directory.

    * On macOS, this raises a FileNotFoundError.

    :return: Path to the Start Menu or None if not found.
    :raises FileNotFoundError: If attempted on macOS.
    :raises TypeError: If winreg value for Start Menu shell folder is not a string/path.
    """
    import os
    import sys

    # Assume that once found, the start menu path does not change
    if hasattr(get_start_menu_path, '__cached__'):
        return get_start_menu_path.__cached__

    platform: str = sys.platform.lower()
    start_menu: Path

    if platform == 'darwin':
        raise FileNotFoundError('macOS has no Start Menu folder.')

    if platform == 'win32':
        shell_folder_key = r'HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
        start_menu = Path.home() / 'AppData/Roaming/Microsoft/Windows/Start Menu'

        try:
            val = get_winreg_value(shell_folder_key, 'Start Menu')
            if not isinstance(val, str):
                raise TypeError(f'Winreg value of {shell_folder_key}\\Start Menu is not a string.')

            # Make sure the path is resolved
            start_menu = Path(val).resolve(True).absolute()

        except (ImportError, OSError):
            pass  # Return the default windows path if the registry couldn't be read.

    else:  # Linux
        home: Path = Path.home() or Path(os.environ['HOME'])

        start_menu = home / '.local/share/applications'

    get_start_menu_path.__cached__ = start_menu
    return start_menu


def get_winreg_value(key_name: str, value_name: str) -> str | int | bytes | list | None:
    """Get a value from the Windows registry.

    :param key_name: The registry key to read. The parent key must be the name of a defined winreg constant.
    :param value_name: The value to read.
    :return: The value, or None if not found.
    :raises AttributeError: If the parent_key is not a defined winreg constant.
    :raises ImportError: If winreg is not available.
    :raises OSError: If the registry key could not be read.
    """
    # noinspection PyCompatibility
    import winreg
    from os.path import expandvars

    parent_key: int = getattr(winreg, key_name.split('\\')[0])
    sub_key: str = '\\'.join(key_name.split('\\')[1:])
    if not isinstance(parent_key, int):
        raise AttributeError('parent_key is not a defined winreg constant.')

    reg_key = winreg.OpenKey(parent_key, sub_key, 0, winreg.KEY_QUERY_VALUE)
    val, reg_type = winreg.QueryValueEx(reg_key, value_name)

    reg_key.Close()

    # Expand environment variables
    if reg_type == winreg.REG_EXPAND_SZ:
        val = expandvars(val)

    return val


# pylint: disable=R
def hide_windows_file(file_path: Path | str, *, unhide: bool = False) -> int | None:
    """Hide an existing Windows file. If not running windows, do nothing.

    Use unhide kwarg to reverse the operation

    :param file_path: Absolute or relative path to hide.
    :param unhide: Unhide a hidden file in Windows.
    :return: None if not on Windows, else if the function succeeds, the return value is nonzero.
    """
    import sys

    # Resolve string path to use with kernel32
    file_path = str(Path(file_path).resolve())
    if sys.platform == 'win32':
        from ctypes import windll

        # File flags are a 32-bit bitarray, the "hidden" attribute is the 2nd least significant bit
        FILE_ATTRIBUTE_HIDDEN = 0b00000000000000000000000000000010

        # bitarray for boolean flags representing file attributes
        current_attributes: int = windll.kernel32.GetFileAttributesW(file_path)
        if not unhide:
            # Add hide attribute to bitarray using bitwise OR
            # 0b00000000 -> 0b00000010 ---- 0b00000110 -> 0b00000110
            merged_attributes: int = current_attributes | FILE_ATTRIBUTE_HIDDEN
            return windll.kernel32.SetFileAttributesW(file_path, merged_attributes)
        else:
            # Remove hide attribute from bitarray if it exists
            # Check with bitwise AND; Remove with bitwise XOR
            # 0b00000100 -> 0b00000100 ---- 0b00000110 -> 0b00000100
            # Only Truthy returns (which contain the hidden attribute) will subtract from the bitarray
            is_hidden = bool(current_attributes & FILE_ATTRIBUTE_HIDDEN)
            if is_hidden:
                subtracted_attributes: int = current_attributes ^ FILE_ATTRIBUTE_HIDDEN
                return windll.kernel32.SetFileAttributesW(file_path, subtracted_attributes)


def patch_windows_taskbar_icon(app_id: str = '') -> int | None:
    """Override Python's default Windows taskbar icon with the custom one set by the app window.

    See:
    https://docs.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid
    for more information.

    :param app_id: Pointer to the AppUserModelID to assign to the current process.
    :return: None if not on Windows, S_OK if this function succeeds. Otherwise, it returns an HRESULT error code.
    """
    import sys

    if sys.platform == 'win32':
        from ctypes import windll
        return windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
