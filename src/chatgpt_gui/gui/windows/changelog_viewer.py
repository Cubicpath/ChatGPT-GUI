###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ReadmeViewer implementation."""
from __future__ import annotations

__all__ = (
    'ChangelogViewer',
)

import random

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ..._version import __version__
from ...models import DeferredCallable
from ...models import DistributedCallable
from ...network import Response
from ...utils import init_layouts
from ...utils import init_objects
from ..aliases import app
from ..aliases import tr
from ..widgets import ExternalTextBrowser


class ChangelogViewer(QWidget):
    """Widget that formats and shows the project's README.md, stored in the projects 'Description' metadata tag."""

    def __init__(self, *args, **kwargs) -> None:
        """Create a new :py:class:`ChangelogViewer` and initialize UI."""
        super().__init__(*args, **kwargs)
        self.resize(QSize(600, 800))
        self.setWindowTitle(tr('gui.changelog_viewer.title'))
        self.setWindowIcon(app().get_theme_icon('message_information') or
                           self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))

        self.changelog_url: str = 'https://raw.githubusercontent.com/Cubicpath/ChatGPT-GUI/master/CHANGELOG.md'
        self.latest_version: str = __version__
        self.text_browser: ExternalTextBrowser
        self._init_ui()

    def _init_ui(self) -> None:
        self.text_browser = ExternalTextBrowser(self)
        self.version_label = QLabel(self)

        init_objects({
            self.text_browser: {
                'font': QFont(self.text_browser.font().family(), 10),
                'openExternalLinks': True
            },

            (check_latest_button := QPushButton(self)): {
                'size': {'fixed': (20, 20)},
                'icon': self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
                'clicked': DistributedCallable((
                    DeferredCallable(app().version_checker.check_version),
                    check_latest_button.setDisabled,
                    self.version_label.setDisabled
                ), True)
            },

            (spacer := QSpacerItem(0, 0, hData=QSizePolicy.Policy.MinimumExpanding)): {},

            (github_button := QPushButton(self)): {
                'size': {'fixed': (180, None)},
                'clicked': DeferredCallable(
                    QDesktopServices.openUrl,
                    QUrl('https://github.com/Cubicpath/ChatGPT-GUI/blob/master/CHANGELOG.md')
                )
            },

            (releases_button := QPushButton(self)): {
                'size': {'fixed': (110, None)},
                'clicked': DeferredCallable(
                    QDesktopServices.openUrl,
                    QUrl('https://github.com/Cubicpath/ChatGPT-GUI/releases')
                )
            }
        })

        app().init_translations({
            self.setWindowTitle: 'gui.changelog_viewer.title',
            self.version_label.setText: ('gui.changelog_viewer.current_version', self.latest_version, __version__),
            github_button.setText: 'gui.changelog_viewer.github',
            releases_button.setText: 'gui.changelog_viewer.releases'
        })

        init_layouts({
            (buttons := QHBoxLayout()): {
                'items': [check_latest_button, self.version_label, spacer, github_button, releases_button]
            },

            # Main layout
            QVBoxLayout(self): {
                'items': [buttons, self.text_browser]
            }
        })

        app().version_checker.newerVersion.connect(self.update_changelog)
        app().version_checker.newerVersion.connect(self.update_latest_version)
        app().version_checker.checked.connect(lambda: QTimer.singleShot(random.randint(250, 500), DistributedCallable((
            check_latest_button.setDisabled,
            self.version_label.setDisabled
        ), False)))

        self.update_changelog()

    def update_changelog(self) -> None:
        """Update the displayed text to the data from the changelog url."""

        def handle_reply(reply: Response):
            text: str = reply.text
            # Add separators between versions and remove primary header
            text = '## ' + '\n-----\n## '.join(text.split('\n## ')[1:])

            # The Markdown Renderer doesn't accept headers with ref_links, so remove them
            new_lines = []
            for line in text.splitlines():
                if line.startswith('## '):
                    line = line.replace('[', '', 1).replace(']', '', 1)

                new_lines.append(line)
            text = '\n'.join(new_lines)

            self.text_browser.set_hot_reloadable_text(text, 'markdown')

        app().session.get(self.changelog_url, finished=handle_reply)

    def update_latest_version(self, _, version: str) -> None:
        """Update the latest version displayed at the top of the changelog to the given string.

        :param version: Latest version string to display
        """
        self.latest_version = version

        text = tr('gui.changelog_viewer.current_version', self.latest_version, __version__)
        self.version_label.setText(f'<b>{text.split("|")[0]}</b>|{text.split("|")[1]}')
