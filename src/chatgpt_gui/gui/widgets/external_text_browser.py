###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""ExternalTextBrowser implementation."""
from __future__ import annotations

__all__ = (
    'ExternalTextBrowser',
)

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from ..aliases import app
from ...constants import *
from ...models import DeferredCallable
from ...network import Response


class ExternalTextBrowser(QTextBrowser):
    """:py:class:`QTextBrowser` with ability to map keys to :py:class:`Callable`'s.

    Also supports external image loading and caching.
    """

    remote_image_cache: dict[str, bytes] = {}

    def __init__(self, *args, **kwargs) -> None:
        """Initialize :py:class:`ExternalTextBrowser` values."""
        super().__init__(*args, **kwargs)
        self.anchorClicked.connect(  # pyright: ignore[reportGeneralTypeIssues]
            lambda url: self.scrollToAnchor(url.toDisplayString().lstrip('#'))
        )

        # default factory producing empty DeferredCallables
        self.key_callable_map: defaultdict[int, Callable] = defaultdict(DeferredCallable)
        self.inject_markdown_anchors: bool = True
        self.cached_text: str = ''
        self.cached_type: str = ''

    def hot_reload(self) -> None:
        """Reload cached text using the cached type's function."""
        # Remember scroll position
        scroll = self.verticalScrollBar().sliderPosition()

        # Reload all resources and replace text with cached text
        self.clear()
        match self.cached_type:
            case 'markdown':
                self.setMarkdown(self.cached_text)
            case 'html':
                self.setHtml(self.cached_text)
            case 'text':
                self.setPlainText(self.cached_text)
        self.verticalScrollBar().setSliderPosition(scroll)

    def set_hot_reloadable_text(self, text: str, text_type: str) -> None:
        """Set text that is designated to be hot-reloadable.

        Injects html anchors to images to allow clickable images.
        Injects html anchors to markdown headers to allow relative linking.
        """
        # Inject html anchors in images and headers
        if text_type == 'markdown':
            lines: list[str] = text.splitlines()
            lines_new: list[str] = []
            ref_links: dict[str, tuple[str, str | None]] = {
                match['label']: (match['url'], match['description'])
                for match in MARKDOWN_REF_LINK_PATTERN.finditer(text)
            }

            for i, line in enumerate(lines):

                # Replace image links with clickable anchor images
                if match := MARKDOWN_IMG_LINK_PATTERN.match(line):
                    # Get ref_link or normal link for anchor href
                    stripped_groups = tuple(group.strip('()[]') for group in match.groups())
                    alt: str = stripped_groups[0]
                    src: str = stripped_groups[1]
                    link: str = stripped_groups[2]

                    # Get reference link data if applicable
                    link_is_ref: bool = match[0][2].startswith('[')
                    ref_url: str | None = ref_links.get(link, (None, None))[0]
                    ref_desc: str | None = ref_links.get(link, (None, None))[1]

                    # Set href and title
                    href: str
                    title: str

                    if link_is_ref:
                        href = ref_url if ref_url is not None else link
                        title = ref_desc if ref_desc is not None else alt
                    else:
                        href = link
                        title = alt

                    lines_new.append(f'<a href="{href}"><img src="{src}" alt="{alt}" title="{title}"/></a>')
                    continue

                # Find headers and add relative anchors
                if self.inject_markdown_anchors:
                    has_hashtag: bool = line.strip().startswith('#')
                    has_underline: bool = bool(line) and (i < len(lines) - 1) and any(
                        # Line must end and begin with the respective underline
                        lines[i + 1].strip().startswith(line_char) and
                        lines[i + 1].strip().endswith(line_char) for line_char in ('-', '=')
                    )

                    # If line has a header marker, append it with an anchor tag and add it to the new list.
                    # Otherwise, append the unchanged line to the new list.
                    if has_hashtag or has_underline:
                        simple_str: str = line.strip().replace(' ', '-').replace(':', '').lstrip('#').strip('-').lower()

                        lines_new.append(
                            f'{line} <a name="{simple_str}" href="#{simple_str}" '
                            f'style="font-size: 1px; color: transparent">§</a>'
                        )
                        continue

                lines_new.append(line)

            text = '\n'.join(lines_new)

        self.cached_text = text
        self.cached_type = text_type
        self.hot_reload()

    def loadResource(self, resource_type: int, url: QUrl, **kwargs) -> Any:
        """Load a resource from an url.

        If resource type is an image and the url is external, download it using requests and cache it.
        """
        # See: https://github.com/Cubicpath/ChatGPT-GUI/pull/30#issuecomment-1279562460
        # QTextDocument.ResourceType.ImageResource = 0x2
        if resource_type == 0x2 and not url.isLocalFile():
            image: QImage = QImage()
            if (url_string := url.toDisplayString()) not in self.remote_image_cache:
                # Add placeholder bytes to show the url is being downloaded.
                # Otherwise, unneeded replies are sent out and cause application stutter.
                self.remote_image_cache[url_string] = b''

                def handle_reply(reply: Response):
                    image.loadFromData(reply.data)
                    self.remote_image_cache[url_string] = reply.data

                    if self.cached_type:
                        self.hot_reload()

                app().session.get(url, finished=handle_reply)
            elif cached_data := self.remote_image_cache[url_string]:
                image.loadFromData(cached_data)
            return image

        return super().loadResource(resource_type, url, **kwargs)

    def setLineWrapMode(self, mode: int | QTextEdit.LineWrapMode) -> None:
        """Set the line wrap mode. Allows use of ints."""
        super().setLineWrapMode(QTextEdit.LineWrapMode(mode))

    def connect_key_to(self, key: Qt.Key, func: Callable) -> None:
        """Connect a :py:class:`Callable` to a key press."""
        self.key_callable_map[int(key)] = func

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Execute :py:class:`Callable` mapped to the key press."""
        super().keyPressEvent(event)
        self.key_callable_map[event.key()]()
        event.accept()
