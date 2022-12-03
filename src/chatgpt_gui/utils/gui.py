###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Utilities for GUI elements."""
from __future__ import annotations

__all__ = (
    'add_menu_items',
    'delete_layout_widgets',
    'icon_from_bytes',
    'init_layouts',
    'init_objects',
    'scroll_to_top',
    'set_or_swap_icon',
)

from collections.abc import Iterable
from collections.abc import Sequence
from typing import Any
from typing import Literal
from typing import TypeAlias

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

_LAYOUT_OBJ: TypeAlias = QLayout | QLayoutItem | QWidget

_layout_type_map = {
    QLayout: 'addLayout',
    QLayoutItem: 'addItem',
    QWidget: 'addWidget',
}

_menu_type_map = {
    str: QMenu.addSection,
    QMenu: QMenu.addMenu,
    QAction: QMenu.addAction,
}


def add_menu_items(menu: QMenu, items: Sequence[str | QAction | QMenu]) -> None:
    """Add items to the given menu.

    This uses the associated :py:class:`QMenu` methods for each object's type::

        str: QMenu.addSection,
        QMenu: QMenu.addMenu,
        QAction: QMenu.addAction,


    :param menu: The menu to add items to.
    :param items: The items to add to the menu.
    """
    for obj in items:
        # Find the item's type and associated method.
        for item_type, meth in _menu_type_map.items():

            if isinstance(obj, item_type):
                # Run method and go to next item.
                meth(menu, obj)
                break


def delete_layout_widgets(layout: QLayout) -> None:
    """Delete all widgets in a layout."""
    while (item := layout.takeAt(0)) is not None:
        item.widget().deleteLater()


def icon_from_bytes(data: bytes) -> QIcon:
    """Create a :py:class:`QIcon` from bytes using a :py:class:`QPixmap` as a proxy."""
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    icon = QIcon(pixmap)
    return icon


def init_layouts(layout_data: dict[
    QLayout,
    dict[
        Literal['childLayouts', 'childWidgets', 'items'],
        Sequence[_LAYOUT_OBJ | Sequence]
    ]
]) -> None:
    """Initialize :py:class:`QLayout` hierarchies with the given data.

    The only secondary dictionary keys allowed are ``'childLayouts'``, ``'childWidgets'``, and ``'items'``.

    layout_data should be a dictionary structured like this::

        {
            my_layout1: {},
            my_layout2: {'items': [layout1, widget1, my_layout1, widget2, layout2, widget3]},
            my_layout3: {'childLayouts': [my_layout2], 'childWidgets': [widget4, widget5], 'items': [layout3]},
        }

    :param layout_data: Dictionary containing data used to initialize QLayouts.
    """
    for layout, data in layout_data.items():

        for key, val in data.items():
            match key:
                case 'childLayouts':
                    for _child in val:
                        layout.addChildLayout(_child)  # type: ignore

                case 'childWidgets':
                    for _child in val:
                        layout.addChildWidget(_child)  # type: ignore

                case 'items':
                    for _args in val:
                        if not isinstance(_args, Sequence):
                            _args = (_args,)

                        # Find the item's type and associated method.
                        item_type = type(_args[0])
                        for clazz, method_name in _layout_type_map.items():

                            if issubclass(item_type, clazz):
                                # Run method if exists and go to next item.
                                if hasattr(layout, method_name):
                                    getattr(layout, method_name)(*_args)
                                break


# noinspection PyUnresolvedReferences
def init_objects(object_data: dict[object, dict[str, Any]]) -> None:
    """Initialize :py:class:`QObject` attributes with the given data.

    object_data should be a dictionary structured like this::

        {
            widget1: {'text': 'some.translation.key', 'clicked': on_click},
            widget2: {'text': 'some.translation.key', 'size': {'fixed': (None, 400)}},
            widget3: {'text': string_value, 'pasted': on_paste, 'returnPressed': on_return},
            widget4: {'activated': when_activated, 'size': widget_size, 'items': (
                f'The Number "{i}"' for i in range(1, 11)
            )}
        }

    :param object_data: Dictionary containing data used to initialize basic QObject values.
    """
    # Initialize widget attributes
    for obj, data in object_data.items():
        special_keys = ('items', 'size')
        items, size_dict = (data.get(key) for key in special_keys)

        # Find setter method for all non specially-handled keys
        for key, val in data.items():
            if key in special_keys:
                continue  # Skip special keys

            if hasattr(obj, key):
                # Check if key is a signal on widget
                # If so, connect it to the given function
                if isinstance((attribute := getattr(obj, key)), SignalInstance):
                    if isinstance(val, Iterable):
                        for slot in val:
                            attribute.connect(slot)
                    else:
                        attribute.connect(val)
                    continue

            # Else call setter to update value
            # Capitalize first character of key
            setter_name: str = f'set{key[0].upper()}{key[1:]}'
            getattr(obj, setter_name)(val)

        if items is not None:
            if not isinstance(obj, QComboBox):
                # Set directly for non-dropdowns
                obj.setItems(items)  # type: ignore
            elif hasattr(obj, 'addItems'):
                obj.addItems(items)
            else:
                for key in items:
                    obj.addItem(key)

        # Set size
        if size_dict is not None:
            for size_type in ('minimum', 'maximum', 'fixed'):
                if size_dict.get(size_type) is not None:
                    size: QSize | Sequence[int] = size_dict.get(size_type)
                    if isinstance(size, QSize):
                        # For PySide6.QtCore.QSize objects
                        getattr(obj, f'set{size_type.title()}Size')(size)
                    elif isinstance(size, Sequence):
                        # For lists, tuples, etc. Set width and height separately.
                        # None can be used rather than int to skip a dimension.
                        if size[0]:
                            getattr(obj, f'set{size_type.title()}Width')(size[0])
                        if size[1]:
                            getattr(obj, f'set{size_type.title()}Height')(size[1])


def scroll_to_top(widget: QTextEdit) -> None:
    """Move text cursor to top of text editor."""
    cursor = widget.textCursor()
    cursor.setPosition(0)
    widget.setTextCursor(cursor)


def set_or_swap_icon(mapping: dict[str, QIcon], key: str, value: QIcon):
    """Given a mapping, replace a :py:class:`QIcon` value mapped to the given ``key`` with data from another.

    This keeps the same object references.
    """
    if key in mapping:
        mapping[key].swap(value)
    else:
        mapping[key] = value
