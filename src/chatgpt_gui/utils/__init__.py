###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Utility functions for chatgpt_gui."""
from __future__ import annotations

__all__ = (
    'add_menu_items',
    'bit_rep',
    'create_shortcut',
    'current_requirement_licenses',
    'current_requirement_names',
    'current_requirement_versions',
    'decode_url',
    'delete_layout_widgets',
    'dict_to_cookie_list',
    'dict_to_query',
    'dump_data',
    'encode_url_params',
    'format_tb',
    'get_desktop_path',
    'get_parent_doc',
    'get_start_menu_path',
    'get_winreg_value',
    'guess_json_utf',
    'has_package',
    'hide_windows_file',
    'http_code_map',
    'icon_from_bytes',
    'init_layouts',
    'init_objects',
    'is_error_status',
    'patch_windows_taskbar_icon',
    'query_to_dict',
    'quote_str',
    'return_arg',
    'scroll_to_top',
    'set_or_swap_icon',
    'unique_values',
    'wait_for_reply',
)

from .common import bit_rep
from .common import dump_data
from .common import format_tb
from .common import get_parent_doc
from .common import return_arg
from .common import quote_str
from .common import unique_values
from .gui import add_menu_items
from .gui import delete_layout_widgets
from .gui import icon_from_bytes
from .gui import init_layouts
from .gui import init_objects
from .gui import scroll_to_top
from .gui import set_or_swap_icon
from .network import decode_url
from .network import dict_to_cookie_list
from .network import dict_to_query
from .network import encode_url_params
from .network import guess_json_utf
from .network import http_code_map
from .network import is_error_status
from .network import query_to_dict
from .network import wait_for_reply
from .package import current_requirement_licenses
from .package import current_requirement_names
from .package import current_requirement_versions
from .package import has_package
from .system import create_shortcut
from .system import get_desktop_path
from .system import get_start_menu_path
from .system import get_winreg_value
from .system import hide_windows_file
from .system import patch_windows_taskbar_icon
