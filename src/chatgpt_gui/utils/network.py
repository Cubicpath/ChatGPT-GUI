###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Utilities for networking."""
from __future__ import annotations

__all__ = (
    'decode_url',
    'dict_to_cookie_list',
    'dict_to_query',
    'encode_url_params',
    'guess_json_utf',
    'http_code_map',
    'is_error_status',
    'query_to_dict',
    'wait_for_reply',
)

import codecs
from http import HTTPStatus
from urllib.parse import unquote as decode_url
from urllib.parse import urlencode as encode_url_params

from PySide6.QtCore import *
from PySide6.QtNetwork import *

# pylint: disable=not-an-iterable
http_code_map = {status.value: (status.phrase, status.description) for status in HTTPStatus}
for _value, _description in {
        400: 'Your search path has malformed syntax or bad characters.',
        401: 'No permission -- Your API token is most likely invalid.',
        403: 'Request forbidden -- You cannot get this resource with or without an API token.',
        404: 'No resource found at the given location.',
        405: 'Invalid method -- GET requests are not accepted for this resource.',
        406: 'Client does not support the given resource format.',
}.items():
    http_code_map[_value] = (http_code_map[_value][0], _description)
    del _value, _description


def dict_to_cookie_list(cookie_values: dict[str, str]) -> list[QNetworkCookie]:
    """Transform a name and value pair into a list of :py:class:`QNetworkCookie` objects."""
    return [QNetworkCookie(
        name=name.encode('utf8'),
        value=value.encode('utf8')
    ) for name, value in cookie_values.items()]


# noinspection PyTypeChecker
def dict_to_query(params: dict[str, str]) -> QUrlQuery:
    """Transform a param name and value pair into a :py:class:`QUrlQuery` object."""
    query = QUrlQuery()
    query.setQueryItems(list(params.items()))
    return query


# noinspection PyTypeChecker
def query_to_dict(query: QUrlQuery | str) -> dict[str, str]:
    """Translate a query string with the format of QUrl.query() to a dictionary representation."""
    if isinstance(query, QUrlQuery):
        query = query.query()
    query = query.lstrip('?')

    return {} if not query else dict(
        pair.split('=') for pair in query.split('&')
    )


def is_error_status(status: int) -> bool:
    """Return True if the HTTP status code is an error status."""
    return 400 <= status < 600


def wait_for_reply(reply: QNetworkReply) -> None:
    """Process events until the reply is finished.

    :param reply: The QNetworkReply to wait for.
    :raises RuntimeError: If the internal C++ QNetworkRequest is deleted.
    """
    while not reply.isFinished():
        QCoreApplication.processEvents()

##########
# NOTICE:
##########
# Requests
# Copyright 2019 Kenneth Reitz
# Apache 2.0 License
# https://github.com/psf/requests/blob/main/LICENSE


# pylint: disable=consider-using-assignment-expr
def guess_json_utf(data: bytes) -> str | None:
    """:return: String representing the detected encoding of the given data. None if not detected."""
    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.
    sample: bytes = data[:4]

    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return 'utf-32'     # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return 'utf-8-sig'  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return 'utf-16'     # BOM included

    match sample.count(b'\x00'):
        case 0:
            return 'utf-8'

        case 2:
            if sample[::2] == b'\x00\x00':   # 1st and 3rd are null
                return 'utf-16-be'
            if sample[1::2] == b'\x00\x00':  # 2nd and 4th are null
                return 'utf-16-le'

        case 3:
            if sample[:3] == b'\x00\x00\x00':  # First 3 are null
                return 'utf-32-be'
            if sample[1:] == b'\x00\x00\x00':  # Last 3 are null
                return 'utf-32-le'

    return None
