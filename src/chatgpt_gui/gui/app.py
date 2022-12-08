###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Module for the main application classes."""
from __future__ import annotations

__all__ = (
    'GetterApp',
    'Theme',
)

import json
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from typing import Final
from typing import NamedTuple
from typing import TypeAlias

import toml
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from .._version import __version__
from ..constants import *
from ..events import EventBus
from ..lang import Translator
from ..models import DeferredCallable
from ..models import DistributedCallable
from ..models import Singleton
from ..network import Client
from ..network import NetworkSession
from ..network import Response
from ..network import VersionChecker
from ..tomlfile import CommentValue
from ..tomlfile import PathTomlDecoder
from ..tomlfile import PathTomlEncoder
from ..tomlfile import TomlEvents
from ..tomlfile import TomlFile
from ..tomlfile import TomlValue
from ..utils import has_package
from ..utils import hide_windows_file
from ..utils import http_code_map
from ..utils import icon_from_bytes
from ..utils import set_or_swap_icon

_DEFAULTS_FILE: Final[Path] = CG_RESOURCE_PATH / 'default_settings.toml'
_LAUNCHED_FILE: Final[Path] = CG_CONFIG_PATH / '.LAUNCHED'
_SETTINGS_FILE: Final[Path] = CG_CONFIG_PATH / 'settings.toml'

_ButtonsWithRoles: TypeAlias = (
    Sequence[tuple[QAbstractButton, QMessageBox.ButtonRole] | QMessageBox.StandardButton] |
    QMessageBox.StandardButton
)


class _DialogResponse(NamedTuple):
    """Response object for GetterApp.show_dialog()."""

    button: QAbstractButton | QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton
    role: QMessageBox.ButtonRole = QMessageBox.ButtonRole.InvalidRole


class Theme(NamedTuple):
    """Object containing data about a Theme."""

    id: str
    style: str
    display_name: str


class GetterApp(Singleton, QApplication):
    """The main ChatGPT-GUI PySide application that runs in the background and manages the process.

    :py:class:`GetterApp` is a singleton and can be accessed via the class using the
    GetterApp.instance() class method or the app() function.
    """

    _singleton_base_type = QApplication
    _singleton_check_ref = False
    updateTranslations = Signal()

    # PyCharm detects dict literals in __init__ as a dict[str, EventBus[TomlEvent]], for no explicable reason.
    # noinspection PyTypeChecker
    def __init__(self, *args: str) -> None:
        """Create a new app with the given arguments and settings."""
        super().__init__(list(args))  # Despite documentation saying it takes in a Sequence[str], it only accepts lists
        self.setApplicationName(CG_PACKAGE_NAME)
        self.setApplicationVersion(__version__)

        self._first_launch: bool = not _LAUNCHED_FILE.is_file()  # Check if launched marker exists
        self._legacy_style: str = self.styleSheet()              # Set legacy style before it is overridden
        self._thread_pool: QThreadPool = QThreadPool.globalInstance()

        self._setting_defaults: dict[str, TomlValue | CommentValue] = toml.loads(
            _DEFAULTS_FILE.read_text(encoding='utf8'), decoder=PathTomlDecoder()
        )
        self._registered_translations: DistributedCallable[set, None, None] = DistributedCallable(set())
        self._windows: dict[str, QWidget] = {}

        # Create all files/directories that are needed for the app to run
        self._create_paths()

        # Must have themes up before load_env
        self.icon_store: defaultdict[str, QIcon] = defaultdict(QIcon)  # Null icon generator
        self.session: NetworkSession = NetworkSession(self)
        self.settings: TomlFile = TomlFile(_SETTINGS_FILE, default=self._setting_defaults)  # type: ignore
        self.themes: dict[str, Theme] = {}
        self.theme_index_map: dict[str, int] = {}
        self.translator: Translator
        self.version_checker: VersionChecker = VersionChecker(self)

        # Correct malformed language tag with default language selected by Translator
        try:
            self.translator = Translator(self.settings['language'])  # type: ignore
        except ValueError:
            self.translator = Translator()
            self.settings['language'] = self.translator.language.tag
            self.settings.save()

        # Load resources from disk
        self.load_themes()  # Depends on icon_store, settings, themes, theme_index_map
        self.load_icons()   # Depends on icon_store, session

        # Register callables to events
        EventBus['settings'] = self.settings.event_bus
        EventBus['settings'].subscribe(
            DeferredCallable(self.load_themes),
            TomlEvents.Import)

        EventBus['settings'].subscribe(
            DeferredCallable(self.updateTranslations.emit),
            TomlEvents.Import)

        EventBus['settings'].subscribe(
            DeferredCallable(self.update_stylesheet),
            TomlEvents.Set, event_predicate=lambda e: e.key == 'gui/themes/selected')

        self.updateTranslations.connect(lambda: self.translator.__setattr__('language', self.settings['language']))
        self.updateTranslations.connect(lambda: self.setApplicationDisplayName(self.translator('app.name')))
        self.updateTranslations.connect(self._registered_translations)
        self.updateTranslations.connect(self._translate_http_code_map)

        if not self.settings['ignore_updates']:
            self.version_checker.newerVersion.connect(self._upgrade_version_dialog)

        # Must load client last, but before windows
        self.load_env(verbose=True)
        self.client = Client(self)
        self._connect_authenticator()

        # Setup window instances
        self._create_windows()
        self.updateTranslations.emit()

    @property
    def first_launch(self) -> bool:
        """Return whether this is the first launch of the application.

        This is determined by checking if the .LAUNCHED file exists in the user's config folder.
        """
        return self._first_launch

    @property
    def windows(self) -> dict[str, QWidget]:
        """Return a copy of the self._windows dictionary."""
        return self._windows.copy()

    def _connect_authenticator(self) -> None:
        self.client.authenticationRequired.connect(
            lambda: self.show_dialog('warnings.empty_token')
        )

        self.client.authenticator.authenticationSuccessful.connect(
            lambda _, user: self.show_dialog('information.authentication_success', description_args=(user.email,))
        )

        self.client.authenticator.authenticationFailed.connect(
            lambda email, e: self.show_dialog('errors.authentication_failed', description_args=(email, e))
        )

    def _create_paths(self) -> None:
        """Create files and directories if they do not exist."""
        for dir_path in (CG_CACHE_PATH, CG_CONFIG_PATH):
            if not dir_path.is_dir():
                dir_path.mkdir(parents=True)

        if self.first_launch:
            # Create first-launch marker
            _LAUNCHED_FILE.touch()
            hide_windows_file(_LAUNCHED_FILE)

        if not _SETTINGS_FILE.is_file():
            # Write default_settings to user's SETTINGS_FILE
            with _SETTINGS_FILE.open(mode='w', encoding='utf8') as file:
                toml.dump(self._setting_defaults, file, encoder=PathTomlEncoder())

    def _create_windows(self) -> None:
        """Create window instances."""
        from .windows import AppWindow
        from .windows import ChangelogViewer
        from .windows import LicenseViewer
        from .windows import ReadmeViewer
        from .windows import SettingsWindow
        from .windows import SignInDialog

        SettingsWindow.create(QSize(420, 600))
        AppWindow.create(QSize(
            # Size to use, with a minimum of 100x100
            max(self.settings['gui/window/x_size'], 100),  # type: ignore
            max(self.settings['gui/window/y_size'], 100)   # type: ignore
        ))

        self._windows['sign_in'] = SignInDialog()
        self._windows['changelog_viewer'] = ChangelogViewer()
        self._windows['license_viewer'] = LicenseViewer()
        self._windows['readme_viewer'] = ReadmeViewer()
        self._windows['settings'] = SettingsWindow.instance()  # type: ignore
        self._windows['app'] = AppWindow.instance()            # type: ignore

    def _translate_http_code_map(self) -> None:
        """Translate the HTTP code map to the current language."""
        for code in (400, 401, 403, 404, 405, 406):
            http_code_map[code] = (http_code_map[code][0], self.translator(f'network.http.codes.{code}.description'))

    def init_translations(self, translation_calls: dict[Callable, str | tuple[Any, ...]]) -> None:
        """Initialize the translation of all objects.

        Register functions to call with their respective translation keys.
        This is used to translate everything in the GUI.
        """
        for func, args in translation_calls.items():
            if not isinstance(args, tuple):
                args = (args,)

            # Call the function with the deferred translation of the given key.
            translate = DeferredCallable(func, DeferredCallable(self.translator, *args))

            # Register the object for dynamic translation
            self._registered_translations.callables.add(translate)

    def update_stylesheet(self) -> None:
        """Set the application stylesheet to the one currently selected in settings."""
        try:
            self.setStyleSheet(self.themes[self.settings['gui/themes/selected']].style)  # type: ignore
        except KeyError:
            self.settings['gui/themes/selected'] = 'legacy'
            self.setStyleSheet(self._legacy_style)

    def show_dialog(self, key: str, parent: QWidget | None = None,
                    buttons: _ButtonsWithRoles | None = None,
                    default_button: QAbstractButton | QMessageBox.StandardButton | None = None,
                    title_args: Sequence | None = None,
                    description_args: Sequence | None = None,
                    details_text: str = '') -> _DialogResponse:
        r"""Show a dialog. This is a wrapper around QMessageBox creation.

        The type of dialog icon depends on the key's first section.
        The following sections are supported::
            - 'about':      -> QMessageBox.about
            - 'questions'   -> QMessageBox.Question
            - 'information' -> QMessageBox.Information
            - 'warnings'    -> QMessageBox.Warning
            - 'errors'      -> QMessageBox.Critical

        The dialog title and description are determined from the
        "title" and "description" child sections of the given key.

        Example with given key as "questions.key"::
            "questions.key.title": "Question Title"\n
            "questions.key.description": "Question Description"

        WARNING: If a StandardButton is clicked, the button returned is NOT a StandardButton enum, but a QPushButton.

        :param key: The translation key to use for the dialog.
        :param parent: The parent widget to use for the dialog. If not supplied, a dummy widget is temporarily created.
        :param buttons: The buttons to use for the dialog. If button is not a StandardButton,
          it should be a tuple containing the button and its role.
        :param default_button: The default button to use for the dialog.
        :param title_args: The translation arguments used to format the title.
        :param description_args: The translation arguments used to format the description.
        :param details_text: If provided, a new 'Show Details...' button will show this text in the dialog when pressed.
        :return: The button that was clicked, as well as its role. None if the key's first section is "about".
        :raises TypeError: If default_button is not a QPushButton or a QStandardButton.
        """
        using_dummy_widget: bool = False
        if parent is None:
            parent = QWidget(None)
            using_dummy_widget = True

        title_args = () if title_args is None else title_args
        description_args = () if description_args is None else description_args

        icon: QMessageBox.Icon
        first_section: str = key.split('.')[0]
        match first_section:
            case 'questions':
                icon = QMessageBox.Icon.Question
            case 'information':
                icon = QMessageBox.Icon.Information
            case 'warnings':
                icon = QMessageBox.Icon.Warning
            case 'errors':
                icon = QMessageBox.Icon.Critical
            case _:
                icon = QMessageBox.Icon.NoIcon

        title_text: str = self.translator(f'{key}.title', *title_args)
        description_text: str = self.translator(f'{key}.description', *description_args)

        # Create custom QMessageBox
        msg_box = QMessageBox(icon, title_text, description_text, parent=parent)
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        if details_text:
            msg_box.setDetailedText(details_text)

        # If no icon is selected, it follows the precedence of QMessagebox.about(). That being:
        # 1. It prefers parent.icon() if that exists.
        # 2. If not, it tries the top-level widget containing parent.
        # 3. If that fails, it tries the PySide6.QtWidgets.QApplication.activeWindow()
        # 4. As a last resort it uses the Information icon.
        if icon is QMessageBox.Icon.NoIcon:
            for widget in (parent, parent.topLevelWidget(), QApplication.activeWindow()):
                if not (about_icon := widget.windowIcon()).isNull():
                    msg_box.setIconPixmap(about_icon.pixmap(999))
                    break
            else:
                msg_box.setIcon(QMessageBox.Icon.Information)

        # Assemble the buttons in the correct order.
        standard_buttons = None
        if buttons is not None:
            if isinstance(buttons, Sequence):
                # If the button is not a tuple, assume it's a QMessageBox.StandardButton.
                # Build a StandardButtons from all StandardButton objects in buttons.
                for button in buttons:
                    if isinstance(button, tuple):
                        msg_box.addButton(button[0], button[1])
                    elif standard_buttons is None:
                        standard_buttons = button
                    else:
                        standard_buttons |= button
            else:
                # If the buttons is not a sequence, assume it's QMessageBox.StandardButtons.
                standard_buttons = buttons

        if standard_buttons:
            msg_box.setStandardButtons(standard_buttons)

        if default_button is not None:
            if not isinstance(default_button, (QPushButton, QMessageBox.StandardButton)):
                raise TypeError(f'Default button cannot be of type: {type(default_button)}')

            msg_box.setDefaultButton(default_button)

        # Add buttonClicked result to list to extract as variable.
        # This works as msg_box.exec() blocks the event loop until finished.
        msg_box.buttonClicked.connect((result := []).append)  # pyright: ignore[reportGeneralTypeIssues]
        msg_box.exec()

        # Get data from result to create a _DialogResponse from
        response_kwargs = {}
        if result:
            response_kwargs['button'] = result[0]
            response_kwargs['role'] = msg_box.buttonRole(result[0])

        # If parent wasn't specified, delete the dummy widget.
        # This will also delete any button objects attached to the QMessageBox.
        if using_dummy_widget:
            # noinspection PyUnboundLocalVariable
            parent.deleteLater()

        return _DialogResponse(**response_kwargs)

    def missing_package_dialog(self, package: str, reason: str | None = None, parent: QWidget | None = None) -> None:
        """Show a dialog informing the user that a package is missing and asks to install said package.

        If a user presses the "Install" button, the package is installed.

        :param package: The name of the package that is missing.
        :param reason: The reason why the package is attempting to be used.
        :param parent: The parent widget to use for the dialog. If not supplied, a dummy widget is temporarily created.
        """
        exec_path = Path(sys.executable)

        install_button = QPushButton(
            self.get_theme_icon('dialog_ok'),
            self.translator('errors.missing_package.install')
        )

        consent_to_install: bool = self.show_dialog(
            'errors.missing_package', parent, (
                (install_button, QMessageBox.ButtonRole.AcceptRole),
                QMessageBox.StandardButton.Cancel
            ),
            default_button=QMessageBox.StandardButton.Cancel,
            description_args=(package, reason, exec_path)
        ).role == QMessageBox.ButtonRole.AcceptRole

        if consent_to_install:
            try:
                # Install the package, Path(sys.executable) contains 0 user input.
                subprocess.run(  # nosec B603:subprocess_without_shell_equals_true
                    (exec_path, '-m', 'pip', 'install', package),
                    check=True
                )
            except (OSError, subprocess.SubprocessError) as e:
                self.show_dialog(
                    'errors.package_install_failure', parent,
                    description_args=(package, e)
                )
            else:
                self.show_dialog(
                    'information.package_installed', parent,
                    description_args=(package,)
                )

    def _upgrade_version_dialog(self, _, version: str) -> None:
        ignore_button = QPushButton(
            self.translator('information.upgrade_version.ignore')
        )

        upgrade_button = QPushButton(
            self.get_theme_icon('dialog_ok'),
            self.translator('information.upgrade_version.upgrade')
        )

        match self.show_dialog(
            'information.upgrade_version', None, (
                (upgrade_button, QMessageBox.ButtonRole.YesRole),
                (ignore_button, QMessageBox.ButtonRole.NoRole),
                QMessageBox.StandardButton.Cancel
            ),
            default_button=QMessageBox.StandardButton.Cancel,
            description_args=(version, __version__)
        ).role:
            case QMessageBox.ButtonRole.YesRole:
                QProcess.execute('pip', arguments=('install', '--upgrade', f'{CG_PACKAGE_NAME.replace("_", "-")}'))
                QProcess.startDetached(sys.executable, arguments=('-m', CG_PACKAGE_NAME))
                self.exit(0)
            case QMessageBox.ButtonRole.NoRole:
                self.version_checker.newerVersion.disconnect(self._upgrade_version_dialog)
                self.settings['ignore_updates'] = True
                self.settings.save()

    def load_env(self, verbose: bool = True) -> None:
        """Load environment variables from .env file."""
        if not has_package('python-dotenv'):
            self.missing_package_dialog('python-dotenv', 'Loading environment variables')
        if not has_package('python-dotenv'):  # During the dialog, the package may be dynamically installed by user.
            return

        from dotenv import load_dotenv
        load_dotenv(verbose=verbose)

    def load_icons(self) -> None:
        """Load all icons needed for the application.

        Fetch locally stored icons from the CG_RESOURCE_PATH/icons directory

        Asynchronously fetch externally stored icons from urls defined in CG_RESOURCE_PATH/external_icons.json
        """
        # Load locally stored icons
        self.icon_store.update({
            filename.stem: QIcon(str(filename)) for
            filename in (CG_RESOURCE_PATH / 'icons').iterdir() if filename.is_file()
        })

        # Load external icon links
        external_icon_links: dict[str, str] = json.loads(
            (CG_RESOURCE_PATH / 'external_icons.json').read_text(encoding='utf8')
        )

        # Load externally stored icons
        # pylint: disable=cell-var-from-loop
        for _key, url in external_icon_links.items():
            # Create a new handler for every key being requested.
            def handle_reply(reply: Response, key=_key):
                icon = icon_from_bytes(reply.data)
                set_or_swap_icon(self.icon_store, key, icon)

            self.session.get(url, finished=handle_reply)

        # Set the default icon for all windows.
        self.setWindowIcon(self.icon_store['openai'])

    def get_theme_icon(self, icon: str) -> QIcon:
        """Return the icon for the given theme.

        :param icon: Icon name for given theme.
        :return: QIcon for the given theme or a null QIcon if not found. Null icons are falsy.
        """
        current_theme = self.settings['gui/themes/selected']
        return self.icon_store[f'cg_theme+{current_theme}+{icon}']

    def add_theme(self, theme: Theme) -> None:
        """Add a theme to the application.

        Overwrites previous theme if the ids are the same.
        """
        self.themes[theme.id] = theme

    def load_themes(self) -> None:
        """Load all theme locations from settings and store them in self.themes.

        Also set current theme from settings.

        :raises ValueError: If gui/themes/{theme}/path setting is not a string.
        """
        self.add_theme(Theme('legacy', self._legacy_style, 'Legacy (Default Qt)'))

        try:
            themes: dict[str, TomlValue] = self.settings['gui/themes']  # type: ignore
        except KeyError:
            self.settings['gui/themes'] = themes = {}

        for id, theme in themes.items():
            if not isinstance(theme, dict):
                continue

            if isinstance((path_ := theme['path']), CommentValue):
                path_ = path_.val

            if not isinstance(path_, str):
                raise ValueError(f'gui/themes/{theme}/path is not a string value.')

            # Translate builtin theme locations
            if path_.startswith('builtin::'):
                path_ = CG_RESOURCE_PATH / f'themes/{path_.removeprefix("builtin::")}'

            # Ensure path is a Path value that exists
            if (path := Path(path_)).is_dir():
                QDir.addSearchPath(f'cg_theme+{id}', path)
                theme_attrs = {
                    'id': id,
                    'style': '',
                    'display_name': theme.get('display_name') or self.translator(f'gui.themes.{id}')
                }

                for theme_resource in path.iterdir():
                    if theme_resource.is_file():
                        if theme_resource.name == 'stylesheet.qss':
                            # Load stylesheet file
                            theme_attrs['style'] = theme_resource.read_text(encoding='utf8')
                        elif theme_resource.suffix.lstrip('.') in SUPPORTED_IMAGE_EXTENSIONS:
                            # Load all images in the theme directory into the icon store.
                            theme_key = f'cg_theme+{id}+{theme_resource.stem}'
                            self.icon_store[theme_key] = QIcon(str(theme_resource.resolve()))

                self.add_theme(Theme(**theme_attrs))

        # noinspection PyUnresolvedReferences
        self.theme_index_map = {theme_id: i for i, theme_id in enumerate(theme.id for theme in self.sorted_themes())}
        self.update_stylesheet()

    def sorted_themes(self) -> list[Theme]:
        """List of themes sorted by their display name."""
        return sorted(self.themes.values(), key=lambda theme: theme.display_name)

    def start_worker(self, runnable: Callable | QRunnable, priority: int = 0) -> None:
        """Start a runnable from the application :py:class:`QThreadPool`."""
        self._thread_pool.start(runnable, priority)
