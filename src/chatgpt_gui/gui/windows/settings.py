###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Settings window implementation."""
from __future__ import annotations

__all__ = (
    'SettingsWindow',
)

from pathlib import Path

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ...constants import *
from ...events import EventBus
from ...models import DeferredCallable
from ...models import DistributedCallable
from ...models import Singleton
from ...tomlfile import TomlEvents
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app
from ..aliases import tr
from ..widgets import PasteLineEdit
from ..widgets import TranslatableComboBox


# noinspection PyTypeChecker
class SettingsWindow(Singleton, QWidget):
    """Window that provides user interaction with the application's settings.

    :py:class:`SettingsWindow` is a singleton and can be accessed via the class using the
    SettingsWindow.instance() class method.
    """

    _singleton_base_type = QWidget
    _singleton_check_ref = False

    def __init__(self, size: QSize) -> None:
        """Create the settings window."""
        super().__init__()

        self.setWindowTitle(tr('gui.settings.title'))
        self.setWindowIcon(app().icon_store['settings'])
        self.resize(size)
        self.setFixedWidth(self.width())

        # Show an error dialog on import failure
        EventBus['settings'].subscribe(
            DeferredCallable(app().show_dialog, 'errors.settings.import_failure', self,
                             description_args=(app().settings.path,)),
            TomlEvents.Fail, event_predicate=lambda event: event.failure == 'import'
        )

        self._init_ui()

    def _init_ui(self) -> None:

        def import_settings() -> None:
            """Import settings from a chosen TOML file."""
            file_path = Path(QFileDialog.getOpenFileName(self, caption=tr('gui.settings.import'),
                                                         dir=str(CG_CONFIG_PATH),
                                                         filter='TOML Files (*.toml);;All files (*.*)')[0])
            if file_path.is_file():
                if app().settings.import_from(file_path):
                    save_button.setDisabled(False)

        def export_settings() -> None:
            """Export current settings to a chosen file location."""
            file_path = Path(QFileDialog.getSaveFileName(self, caption=tr('gui.settings.export'),
                                                         dir=str(CG_CONFIG_PATH),
                                                         filter='TOML Files (*.toml);;All files (*.*)')[0])
            if str(file_path) != '.':
                app().settings.export_to(file_path)

        def hide_token() -> None:
            """Hide session key."""
            self.token_set_button.setDisabled(True)
            self.token_field.setDisabled(True)
            self.token_field.setText(app().client.hidden_token())
            self.token_field.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def toggle_token_visibility() -> None:
            """Toggle hiding and showing the session key."""
            if not self.token_field.isEnabled():
                self.token_field.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self.token_field.setText(app().client.session_token or '')
                self.token_field.setDisabled(False)
                self.token_field.setFocus()
                self.token_set_button.setDisabled(False)
            else:
                hide_token()

        def set_token() -> None:
            """Set the client's session token to the current text in the token field."""
            if text := self.token_field.text().strip():
                self.token_clear_button.setDisabled(False)
                app().client.session_token = text
            else:
                clear_token()
            toggle_token_visibility()

        def clear_token() -> None:
            del app().client.session_token
            hide_token()
            self.token_clear_button.setDisabled(True)

        # Define widget attributes
        # Cannot be defined in init_objects() as walrus operators are not allowed for object attribute assignment.
        # This works in the standard AST, but is a seemingly arbitrary limitation set by the interpreter.
        # See: https://stackoverflow.com/questions/64055314#answer-66617839
        (
            self.token_set_button, self.token_clear_button,
            self.theme_dropdown, self.proxy_protocol_dropdown,
            self.proxy_group, self.proxy_host_field, self.proxy_port_field,
            self.proxy_username_field, self.proxy_password_field, self.token_field
        ) = (
            QPushButton(self), QPushButton(self),
            TranslatableComboBox(self), TranslatableComboBox(self),
            QGroupBox(self), PasteLineEdit(self), PasteLineEdit(self),
            PasteLineEdit(self), PasteLineEdit(self), PasteLineEdit(self)
        )

        init_objects({
            # Labels
            (theme_label := QLabel(self)): {
                'size': {'maximum': (85, None)}
            },

            # Buttons
            (save_button := QPushButton(self)): {
                'disabled': True,
                'size': {'maximum': (50, None)},
                'clicked': app().settings.save
            },
            (reload_button := QPushButton(self)): {
                'size': {'maximum': (60, None)},
                'clicked': app().settings.reload
            },
            (import_button := QPushButton(self)): {
                'clicked': import_settings
            },
            (export_button := QPushButton(self)): {
                'clicked': export_settings
            },
            (open_editor_button := QPushButton(self)): {
                'clicked': DeferredCallable(QDesktopServices.openUrl, lambda: QUrl(app().settings.path.as_uri()))
            },
            (edit_token_button := QPushButton(self)): {
                'clicked': toggle_token_visibility
            },
            self.token_set_button: {
                'size': {'minimum': (40, None)},
                'clicked': set_token
            },
            self.token_clear_button: {
                'disabled': not app().client.session_token,
                'clicked': clear_token
            },

            # Line editors
            self.token_field: {
                'font': QFont('segoe ui', 8), 'text': app().client.hidden_token(),
                'pasted': set_token, 'returnPressed': self.token_set_button.click,
                'size': {'minimum': (220, None)}, 'alignment': Qt.AlignmentFlag.AlignCenter
            },
            self.proxy_host_field: {
                'disabled': not app().settings['network/proxy/protocol']
            },
            self.proxy_port_field: {
                'disabled': not app().settings['network/proxy/protocol'],
                'size': {'maximum': (50, None)}
            },
            self.proxy_username_field: {
                'disabled': not app().settings['network/proxy/protocol']
            },
            self.proxy_password_field: {
                'disabled': not app().settings['network/proxy/protocol'],
                'echoMode': QLineEdit.EchoMode.Password,
            },

            # Dropdowns
            self.theme_dropdown: {
                'activated': DeferredCallable(
                    app().settings.__setitem__,
                    'gui/themes/selected',
                    lambda: app().sorted_themes()[self.theme_dropdown.currentIndex()].id
                ),
                'items': (theme.display_name for theme in app().sorted_themes())
            },
            self.proxy_protocol_dropdown: {
                'activated': DeferredCallable(
                    app().settings.__setitem__,
                    'network/proxy/protocol',
                    self.proxy_protocol_dropdown.currentIndex
                ),
                'items': (
                    'gui.settings.proxy.protocol.none',
                    'gui.settings.proxy.protocol.http',
                    'gui.settings.proxy.protocol.socks5'
                )
            },

            # Groups
            self.proxy_group: {
                'layout': (proxy_group_layout := QVBoxLayout()),
                'flat': True
            }
        })

        app().init_translations({
            self.setWindowTitle: 'gui.settings.title',
            self.proxy_protocol_dropdown.translate_items: '',
            self.theme_dropdown.translate_items: '',
            self.proxy_group.setTitle: 'gui.settings.proxy.general',

            # Labels
            theme_label.setText: 'gui.settings.theme',

            # Line Editors
            self.proxy_host_field.setPlaceholderText: 'gui.settings.proxy.host.placeholder_text',
            self.proxy_port_field.setPlaceholderText: 'gui.settings.proxy.port.placeholder_text',
            self.proxy_username_field.setPlaceholderText: 'gui.settings.proxy.username.placeholder_text',
            self.proxy_password_field.setPlaceholderText: 'gui.settings.proxy.password.placeholder_text',

            # Buttons
            save_button.setText: 'gui.settings.save',
            reload_button.setText: 'gui.settings.reload',
            import_button.setText: 'gui.settings.import',
            export_button.setText: 'gui.settings.export',
            open_editor_button.setText: 'gui.settings.open_editor',
            edit_token_button.setText: 'gui.settings.auth.edit',
            self.token_set_button.setText: 'gui.settings.auth.set',
            self.token_clear_button.setText: 'gui.settings.auth.clear_token'
        })

        init_layouts({
            # Add bottom widgets
            (token_layout := QHBoxLayout()): {
                'items': [self.token_clear_button]
            },
            (key_layout := QHBoxLayout()): {
                'items': [self.token_field, self.token_set_button]
            },
            (bottom := QVBoxLayout()): {
                'items': [edit_token_button, key_layout, token_layout]
            },

            # Add middle widgets
            (theme_layout := QHBoxLayout()): {
                'items': [theme_label, self.theme_dropdown]
            },
            (proxy_server_layout := QHBoxLayout()): {
                'items': [self.proxy_host_field, self.proxy_port_field]
            },
            (proxy_login_layout := QHBoxLayout()): {
                'items': [self.proxy_username_field, self.proxy_password_field]
            },
            proxy_group_layout: {
                'items': [
                    self.proxy_protocol_dropdown,
                    proxy_server_layout,
                    proxy_login_layout
                ]
            },
            (middle := QVBoxLayout()): {
                'items': [theme_layout, self.proxy_group]
            },

            # Add top widgets
            (io_buttons := QHBoxLayout()): {
                'items': [save_button, reload_button, import_button, export_button]
            },
            (top := QVBoxLayout()): {
                'items': [io_buttons, open_editor_button]
            },

            # Main layout
            QGridLayout(self): {
                'items': [
                    (top, 0, 0, Qt.AlignmentFlag.AlignTop),
                    (middle, 10, 0, Qt.AlignmentFlag.AlignTop),
                    (bottom, 20, 0, Qt.AlignmentFlag.AlignBottom)
                ]
            }
        })

        EventBus['settings'].subscribe(DistributedCallable((
            lambda event: self.proxy_host_field.setDisabled(not event.new),
            lambda event: self.proxy_port_field.setDisabled(not event.new),
            lambda event: self.proxy_username_field.setDisabled(not event.new),
            lambda event: self.proxy_password_field.setDisabled(not event.new)
        )), TomlEvents.Set, lambda event: event.key == 'network/proxy/protocol')

        EventBus['settings'].subscribe(
            DeferredCallable(save_button.setDisabled, False),
            TomlEvents.Set, lambda event: event.old != event.new)

        EventBus['settings'].subscribe(
            DeferredCallable(save_button.setDisabled, True),
            TomlEvents.Export, lambda event: event.toml_file.path == event.path)

        EventBus['settings'].subscribe(
            DeferredCallable(save_button.setDisabled, True),
            TomlEvents.Import, lambda event: event.toml_file.path == event.path)

        EventBus['settings'].subscribe(
            DeferredCallable(self.refresh_dropdowns),
            TomlEvents.Import)

    def refresh_dropdowns(self) -> None:
        """Refresh all dropdown widgets with the current settings assigned to them."""
        settings = app().settings
        self.theme_dropdown.setCurrentIndex(app().theme_index_map[settings['gui/themes/selected']])  # type: ignore
        self.proxy_protocol_dropdown.setCurrentIndex(settings['network/proxy/protocol'])             # type: ignore

    # # # # # Events

    def showEvent(self, event: QShowEvent) -> None:
        """Auto hides the key upon un-minimizing."""
        super().showEvent(event)
        self.refresh_dropdowns()

        init_objects({
            self.token_field: {
                'disabled': True,
                'alignment': Qt.AlignmentFlag.AlignCenter,
                'text': app().client.hidden_token()
            },
            self.token_set_button: {'disabled': True},
            self.token_clear_button: {'disabled': not app().client.session_token}
        })

        event.accept()
