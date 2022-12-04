###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Package for managing outgoing requests for chatgpt_gui."""
from __future__ import annotations

__all__ = (
    'gc_response',
    'KNOWN_HEADERS',
    'NetworkSession',
    'Request',
    'Response',
)

import datetime as dt
import json as json_
import re
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from json import dumps as json_dumps
from pathlib import Path
from typing import Any
from typing import Final
from typing import TypeAlias
from warnings import warn
from weakref import WeakKeyDictionary

from PySide6.QtCore import *
from PySide6.QtNetwork import *
from shiboken6 import Shiboken

from ..models import CaseInsensitiveDict
from ..models import DeferredCallable
from ..utils import dict_to_query
from ..utils import encode_url_params
from ..utils import guess_json_utf
from ..utils import is_error_status
from ..utils import query_to_dict
from ..utils import wait_for_reply

_StringPair: TypeAlias = dict[str, str] | list[tuple[str, str]]
_KnownHeaderValues: TypeAlias = (str | bytes | dt.datetime | dt.date | dt.time | _StringPair | list[str])
_HeaderValue: TypeAlias = dict[str, _KnownHeaderValues] | list[tuple[str, _KnownHeaderValues]]

_INT_PATTERN: Final[re.Pattern] = re.compile(r'[1-9]\d*|0')


# autopep8: off
KNOWN_HEADERS: CaseInsensitiveDict[tuple[QNetworkRequest.KnownHeaders, type]] = CaseInsensitiveDict({
    # Name:                Header Enum Value:                                      Object Wanted:
    # -----------------------------------------------------------------------------------------------
    'Content-Disposition': (QNetworkRequest.KnownHeaders.ContentDispositionHeader, str),
    'Content-Type':        (QNetworkRequest.KnownHeaders.ContentTypeHeader,        str),
    'Content-Length':      (QNetworkRequest.KnownHeaders.ContentLengthHeader,      bytes),
    'Cookie':              (QNetworkRequest.KnownHeaders.CookieHeader,             QNetworkCookie),
    'ETag':                (QNetworkRequest.KnownHeaders.ETagHeader,               str),
    'If-Match':            (QNetworkRequest.KnownHeaders.IfMatchHeader,            QStringListModel),
    'If-Modified-Since':   (QNetworkRequest.KnownHeaders.IfModifiedSinceHeader,    QDateTime),
    'If-None-Match':       (QNetworkRequest.KnownHeaders.IfNoneMatchHeader,        QStringListModel),
    'Last-Modified':       (QNetworkRequest.KnownHeaders.LastModifiedHeader,       QDateTime),
    'Location':            (QNetworkRequest.KnownHeaders.LocationHeader,           QUrl),
    'Server':              (QNetworkRequest.KnownHeaders.ServerHeader,             str),
    'Set-Cookie':          (QNetworkRequest.KnownHeaders.SetCookieHeader,          QNetworkCookie),
    'User-Agent':          (QNetworkRequest.KnownHeaders.UserAgentHeader,          str),
})
# autopep8: on


def _translate_header_value(
        header: str, value: _KnownHeaderValues
) -> _KnownHeaderValues | QDateTime | list[QNetworkCookie] | QUrl:
    """Translate a header's value to it's appropriate type for use in QNetworkRequest.setHeader.

    Values are translated to their appropriate type based on the
    type defined in KNOWN_HEADERS next to the header enum value.

    The following types are supported:
        - str: Given value is translated into a str.
        - bytes: Translates string value into a utf8 encoded version.
        - QDateTime: Translates string and datetime values into a QDateTime.
        - QNetworkCookie: Translates string pairs into a QNetworkCookie list.
          The first value is the cookie name, the second is the cookie value.
        - QStringListModel: Iterates over value and translates all inner-values to strings.
          Returns a list of the translated strings.
        - QUrl: Calls the QUrl constructor on value and returns result.

    :param header: Header defined in KNOWN_HEADERS.
    :param value: Value to translate into an accepted type.
    :return: Transformed value.
    """
    # Match the known-header's value name and translate value to that type.
    match KNOWN_HEADERS[header][1].__name__:
        case 'str':
            return str(value)

        case 'bytes':
            if isinstance(value, str):
                return value.encode('utf8')

        case 'QDateTime':
            if isinstance(value, (dt.datetime, dt.date, dt.time)):
                date_value: dt.datetime | dt.date | dt.time = value

                # Translate datetime objects to a string
                if not isinstance(value, dt.datetime):
                    date: dt.date = dt.datetime.now().date() if isinstance(value, dt.time) else value
                    time: dt.time = dt.datetime.now().time() if isinstance(value, dt.date) else value
                    date_value = dt.datetime.fromisoformat(f'{date.isoformat()}T{time.isoformat()}')

                return QDateTime().fromString(date_value.isoformat(), Qt.DateFormat.ISODateWithMs)

            # Translate string to QDateTime object
            return QDateTime().fromString(str(value), Qt.DateFormat.ISODateWithMs)

        case 'QNetworkCookie':
            cookie_list: list[QNetworkCookie] = []
            # Translate mappings
            if isinstance(value, Mapping):
                for name, _value in value.items():
                    cookie_list.append(QNetworkCookie(name.encode('utf8'), _value.encode('utf8')))

            # Translate tuples, lists, etc. that contain two strings (name and value)
            elif isinstance(value, Sequence) and not isinstance(value, (bytes, str)):
                for pair in value:
                    cookie_list.append(QNetworkCookie(pair[0].encode('utf8'), pair[1].encode('utf8')))

            return cookie_list

        case 'QStringListModel':
            if isinstance(value, Sequence):
                return [str(item) for item in value]

        case 'QUrl':
            if not isinstance(value, QUrl):
                return QUrl(str(value))

    return value


def gc_response(func: Callable[[Response], Any]) -> Callable[[Response], Any]:
    """Wrap the given function to delete a :py:class:`Response` after being called.

    This should only be used for one-time calls, such as a "handling reply" function.
    """
    def wrapper(response: Response, *args, **kwargs) -> Any:
        """Call ``delete()`` on first argument after being called."""
        ret_val: Any = func(response, *args, **kwargs)
        response.delete()
        return ret_val

    return wrapper


class NetworkSession:
    """``requests``-like wrapper over a :py:class:`QNetworkAccessManager`.

    The following convenience methods are supported:
        - get
        - head
        - post
        - put
        - delete
        - patch
    """

    def __init__(self, manager_parent: QObject | None = None) -> None:
        """Initialize the NetworkSession.

        :param manager_parent: Parent of the QNetworkAccessManager.
        """
        self._headers = CaseInsensitiveDict()
        self.manager = QNetworkAccessManager(manager_parent)
        self.default_redirect_policy = QNetworkRequest.RedirectPolicy.UserVerifiedRedirectPolicy
        self.reply_auth_map: WeakKeyDictionary[QNetworkReply, tuple[str, str]] = WeakKeyDictionary()

        self.manager.authenticationRequired.connect(self._handle_auth)  # pyright: ignore[reportGeneralTypeIssues]

    @property
    def cookies(self) -> dict[str, str]:
        """Return dictionary representation of the internal QNetworkCookieJar."""
        return {cookie.name().toStdString(): cookie.value().toStdString() for
                cookie in self.manager.cookieJar().allCookies()}

    @cookies.deleter
    def cookies(self) -> None:
        """Clear all cookies on delete."""
        self.clear_cookies()

    @property
    def headers(self) -> CaseInsensitiveDict[Any]:
        """:return: Dictionary containing the default session headers."""
        return self._headers

    @headers.setter
    def headers(self, value: Mapping) -> None:
        """Translate any mapping value to a CaseInsensitiveDict for use as headers.

        :param value: Mapping to copy into a CaseInsensitiveDict.
        :raises TypeError: If the value is not a Mapping.
        """
        if not isinstance(value, Mapping):
            raise TypeError(f'NetworkSession headers must be a Mapping, not {type(value)}')

        self._headers = CaseInsensitiveDict(value)

    @headers.deleter
    def headers(self) -> None:
        """Clear headers on delete."""
        self._headers.clear()

    @staticmethod
    def _check_method_kwargs(method: str, **kwargs) -> None:
        """Check that the given keyword arguments are valid for the given HTTP method.

        If some arguments are invalid, a warning is emitted.

        :param method: HTTP method to check.
        :param kwargs: Keyword arguments to check.
        """
        if method in {'GET', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE'}:
            if any((kwargs.get('data'), kwargs.get('files'), kwargs.get('json'))):
                warn(UserWarning(
                    f'{method} requests do not support data attached to the request body. '
                    f'This data is likely to be ignored.'
                ))

    def _handle_auth(self, reply: QNetworkReply, authenticator: QAuthenticator) -> None:
        if reply in self.reply_auth_map:
            user, password = self.reply_auth_map[reply]
            authenticator.setUser(user)
            authenticator.setPassword(password)

    def clear_cookies(self, domain: str | None = None, path: str | None = None, name: str | None = None) -> bool:
        """Clear some cookies. Functionally equivalent to http.cookiejar.clear.

        Invoking this method without arguments will clear all cookies.  If
        given a single argument, only cookies belonging to that domain will be
        removed.  If given two arguments, cookies belonging to the specified
        path within that domain are removed.  If given three arguments, then
        the cookie with the specified name, path and domain is removed.

        :param domain: The domain of the cookie to remove.
        :param path: The path of the cookie to remove.
        :param name: The name of the cookie to remove.
        :return: True if any cookies were removed, False otherwise.
        :raises ValueError: If name is provided, must provide path.
          If path is provided, must provide domain. Raise otherwise.
        """

        def deletion_predicate(cookie: QNetworkCookie) -> bool:
            """Return whether the cookie should be deleted.

            :param cookie: The cookie to check.
            :return: True if the cookie should be removed, False otherwise.
            :raises ValueError: If name is provided, must provide path.
              If path is provided, must provide domain. Raise otherwise.
            """
            # 3 args -- Delete the specific cookie which matches all information.
            if name is not None:
                if domain is None or path is None:
                    raise ValueError('Must specify domain and path if specifying name')

                return cookie.name().toStdString() == name and cookie.domain() == domain and cookie.path() == path

            # 2 args -- Delete all cookies with the given domain and path.
            if path is not None:
                if domain is None:
                    raise ValueError('Must specify domain if specifying path')

                return cookie.domain() == domain and cookie.path() == path

            # 1 arg -- Delete all cookies in the given domain.
            if domain is not None:
                return cookie.domain() == domain

            # 0 args -- Delete all cookies
            return True

        results = []
        for _cookie in self.manager.cookieJar().allCookies():
            if deletion_predicate(_cookie):
                results.append(self.manager.cookieJar().deleteCookie(_cookie))

        return any(results)

    def set_cookie(self, name: str, value: str, domain: str, path: str | None = None) -> bool:
        """Create a new cookie with the given date.

        Replaces a pre-existing cookie with the same identifier if it exists.

        :return: True if the cookie was set.
        :raises: ValueError if name and value are not strings.
        """
        cookie = QNetworkCookie(name=name.encode('utf8'), value=value.encode('utf8'))
        cookie.setDomain(domain)
        cookie.setPath(path or '/')
        return self.manager.cookieJar().insertCookie(cookie)

    def request(self, method: str, url: QUrl | str, *args, **kwargs) -> Response:
        """Send an HTTP request to the given URL with the given data.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param method: HTTP method/verb to use for the request. Case-sensitive.
        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        send_kwargs = {
            'wait_until_finished': kwargs.pop('wait_until_finished', False),
            'finished': kwargs.pop('finished', None),
            'progress': kwargs.pop('progress', None),
        }

        return Request(method, url, *args, **kwargs).send(self, **send_kwargs)

    def get(self, url: QUrl | str, **kwargs) -> Response:
        """Create and send a request with the GET HTTP method.

        GET is the general method used to get a resource from a server.
        It is the most commonly used method, with GET requests being used by web browsers to
        download HTML pages, images, and other resources.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        method: str = 'GET'
        self._check_method_kwargs(method, **kwargs)

        return self.request(method=method, url=url, **kwargs)

    def head(self, url: QUrl | str, **kwargs) -> Response:
        """Create and send a request with the HEAD HTTP method.

        HEAD requests are used to retrieve information about a resource without actually fetching the resource itself.
        This is useful for checking if a resource exists, or for getting the size of a resource before downloading it.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        method: str = 'HEAD'
        self._check_method_kwargs(method, **kwargs)

        return self.request(method=method, url=url, **kwargs)

    def post(self, url: QUrl | str, **kwargs) -> Response:
        """Create and send a request with the POST HTTP method.

        POST is the general method used to send data to a server.
        It does not require a resource to previously exist, nor does it require one to not exist.
        This makes it very common for servers to accept POST requests for a multitude of things.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        method: str = 'POST'
        self._check_method_kwargs(method, **kwargs)

        return self.request(method=method, url=url, **kwargs)

    def put(self, url: QUrl | str, **kwargs) -> Response:
        """Create and send a request with the PUT HTTP method.

        PUT is a method for completely updating a resource on a server.
        The data sent by PUT should be the full content of the resource.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        method: str = 'PUT'
        self._check_method_kwargs(method, **kwargs)

        return self.request(method=method, url=url, **kwargs)

    def delete(self, url: QUrl | str, **kwargs) -> Response:
        """Create and send a request with the DELETE HTTP method.

        DELETE is used to delete a specified resource.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        method: str = 'DELETE'
        self._check_method_kwargs(method, **kwargs)

        return self.request(method=method, url=url, **kwargs)

    def patch(self, url: QUrl | str, **kwargs) -> Response:
        """Create and send a request with the PATCH HTTP method.

        PATCH is used to send a partial update of an existing resource.

        -----

        See :py:meth:`Request.__init__` for full kwarg documentation.

        :param url: URL to send the request to. Case-sensitive.
        :keyword params: URL parameters to attach to the URL. Case-sensitive.
        :keyword data: Bytes to send in the request body.
        :keyword headers: Headers to use for the request. Case-insensitive.
        :keyword cookies: Cookies to use for the request. Case-sensitive.
        :keyword auth: Optional tuple containing username and password.
        :keyword timeout: Timeouts for the request.
        :keyword allow_redirects: If False, do not follow any redirect requests.
        :keyword proxies: String-pairs mapping protocol to the URL of the proxy.
        :keyword stream: Whether to accept chunked encoding.
        :keyword verify: Whether to verify SSL certificates.
        :keyword cert: Client certificate information.
        :keyword json: JSON data to send in the request body.
        :keyword wait_until_finished: Process the application eventLoop until the reply is finished.
        :keyword finished: Callback when the request finishes, with request supplied as an argument.
        :keyword progress: Callback to update download progress, with the request, received bytes, and total bytes.

        :return: Response object, which is not guaranteed to be finished.
        """
        method: str = 'PATCH'
        self._check_method_kwargs(method, **kwargs)

        return self.request(method=method, url=url, **kwargs)


class Request:
    """``requests``-like wrapper over a :py:class:`QNetworkRequest`."""

    def __init__(self, method: str, url: QUrl | str,
                 params: _StringPair | None = None,
                 data: bytes | _StringPair | None = None,
                 headers: _HeaderValue | None = None,
                 cookies: _StringPair | None = None,
                 # files: dict[str, Any] | None = None,
                 auth: tuple[str, str] | None = None,
                 timeout: float | tuple[float, float] | None = 30.0,
                 allow_redirects: bool = True,
                 proxies: _StringPair | None = None,
                 stream: bool = False,
                 verify: bool | str | None = None,
                 cert: str | tuple[str, str] | None = None,
                 json: dict[str, Any] | None = None) -> None:
        """Create a new :py:class:`Request` with the given fields.

        :param method: HTTP method/verb to use for the request. Case-sensitive.

        :param url: URL to send the request to. Case-sensitive.
            Could be a string or QUrl.

        :param params: URL parameters to attach to the URL. Case-sensitive.
            If url is a QUrl, overrides the QUrl's query.

        :param data: Bytes to send in the request body.
            If a string-pair, will be encoded to bytes as a form-encoded request body.
            Incompatible with the json and files parameters.

        :param headers: Headers to use for the request.
            Non-string values should ONLY be used for KNOWN_HEADERS. Case-insensitive.

        :param cookies: Cookies to use for the request. Case-sensitive.

        :param auth: Optional tuple containing username and password.
            These will be sent to the server if it requests authentication.

        :param timeout: Timeouts for the request.
            If a single float, both the connect and read timeout will be set to this value.
            If a tuple, the first value is the connect timeout and the second value is the read timeout.
            If None or 0, no timeout will be set.

        :param allow_redirects:
            If False, do not follow any redirect requests.

        :param proxies: String-pairs mapping protocol to the URL of the proxy.
            Supported protocols are 'ftp', 'http', 'socks5'.

        :param stream: Whether to accept chunked encoding.
            See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding#chunked_encoding

        :param verify: Whether to verify SSL certificates.
            If False, ignore all SSL errors.
            If a string, interpret verify as a path to the CA bundle to verify certificates against.

        :param cert: Client certificate information.
            If a string, interpret cert as a path to a certificate to use for SSL client authentication.
            If a tuple, interpret cert as a (cert, key) pair.

        :param json: JSON data to send in the request body.
            Automatically encodes to bytes and updates Content-Type header.
            Incompatible with the data and files parameters.
        """
        self._request: QNetworkRequest = QNetworkRequest()

        self.method = method
        self.url = url
        self.params = {} if params is None else dict(params)
        self.data = dict(data) if (isinstance(data, Sequence) and not isinstance(data, (bytes, str))) else data
        self.headers = {} if headers is None else dict(headers)
        self.cookies = {} if cookies is None else dict(cookies)
        # self.files = files
        self.auth = auth
        self.timeout = timeout
        self.allow_redirects = allow_redirects
        self.proxies = None if proxies is None else dict(proxies)
        self.stream = stream
        self.verify = verify
        self.cert = cert
        self.json = json

    def __repr__(self) -> str:
        """Representation of the :py:class:`Request` with method and target URL."""
        return f'<Request [{self.method}] ({self.url})>'

    def _prepare_body(self) -> bytes | None:
        content_type = None
        body: bytes | None = None

        if self.data:
            if isinstance(self.data, dict):
                body = encode_url_params(self.data).encode('utf8')
                content_type = 'application/x-www-form-urlencoded'

            elif isinstance(self.data, bytes):
                body = self.data

        elif self.json is not None:
            body = json_dumps(self.json, allow_nan=False).encode('utf8')
            content_type = 'application/json'

        if content_type and 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = content_type

        return body

    def _prepare_headers(self, headers: CaseInsensitiveDict) -> None:
        if self.stream:
            headers['Transfer-Encoding'] = 'chunked'

        if self.cookies:
            headers['Cookie'] = headers

        for name, value in headers.items():
            if name in KNOWN_HEADERS:
                value = _translate_header_value(name, value)
                self._request.setHeader(KNOWN_HEADERS[name][0], value)
                continue

            try:
                encoded_value = bytes(value) if not isinstance(value, str) else value.encode('utf8')
            except TypeError:
                encoded_value = str(value).encode('utf8')

            self._request.setRawHeader(name.encode('utf8'), encoded_value)

    # pylint: disable=compare-to-zero
    def _prepare_response(
            self,
            reply: QNetworkReply,
            finished: _ResponseConsumer | None,
            progress: _ProgressConsumer | None
    ) -> Response:
        _response = Response(self, reply)

        # Put into variables to ignore incorrect known-type errors
        (reply_redirected, reply_finished, reply_downloadProgress, reply_redirectAllowed) = (
            reply.redirected, reply.finished,              # pyright: ignore[reportGeneralTypeIssues]
            reply.downloadProgress, reply.redirectAllowed  # pyright: ignore[reportGeneralTypeIssues]
        )

        if self.allow_redirects:
            reply_redirected.connect(lambda _: reply_redirectAllowed)

        if self.verify is False:
            reply.ignoreSslErrors()

        if finished is not None:
            reply_finished.connect(DeferredCallable(gc_response(finished), _response))

        if progress is not None:
            reply_downloadProgress.connect(DeferredCallable(progress, _response, _extra_pos_args=2))

        if self.timeout:
            # Create connection timeout timer
            # This is for the RESPONSE side of the connection.
            def handle_connection_timeout():
                if not reply.isFinished():
                    reply.abort()

            connection_timeout = int((self.timeout[0] if isinstance(self.timeout, Sequence) else self.timeout) * 1000)
            timer = QTimer(reply)
            timer.setSingleShot(True)
            timer.setInterval(connection_timeout)
            timer.timeout.connect(handle_connection_timeout)  # pyright: ignore[reportGeneralTypeIssues]
            timer.start()

        return _response

    def _prepare_ssl(self) -> None:
        ssl_config = QSslConfiguration.defaultConfiguration()

        if isinstance(self.verify, str):
            ssl_config.setCaCertificates(QSslCertificate.fromPath(self.verify))

        if isinstance(self.cert, str):
            ssl_config.setLocalCertificateChain(QSslCertificate.fromPath(self.cert))
        elif isinstance(self.cert, tuple):
            # cert is a tuple of (cert_path, key_path)
            ssl_config.setLocalCertificateChain(QSslCertificate.fromPath(self.cert[0]))
            ssl_config.setPrivateKey(QSslKey(Path(self.cert[1]).read_bytes(), QSsl.KeyAlgorithm.Rsa))

        self._request.setSslConfiguration(ssl_config)

    def send(self,
             session: NetworkSession,
             wait_until_finished: bool = False,
             finished: _ResponseConsumer | None = None,
             progress: _ProgressConsumer | None = None
             ) -> Response:
        """Send the :py:class:`Request` using the specified :py:class:`NetworkSession`.

        :param session: Session to use.

        :param wait_until_finished: Process the application eventLoop until
            the reply is finished, so when it is returned you can immediately access data.

        :param finished: Callback when the request finishes,
            with reply supplied as an argument.

        :param progress: Callback to update download progress,
            with the reply, received bytes, and total bytes supplied as arguments.

        :return: Response object, which is not guaranteed to be finished.
        :raises ValueError: If proxy attribute is not a valid option.
        """
        request_url = QUrl(self.url)  # Ensure url is of type QUrl
        request_params = query_to_dict(request_url.query()) | self.params  # Update QUrl params with params argument
        request_headers = session.headers | self.headers                   # Use session headers as default headers
        request_cookies = session.cookies | self.cookies                   # Use session cookies as default cookies
        request_data = self._prepare_body()

        if self.cookies:
            request_headers['Cookie'] = request_cookies

        request_url.setQuery(dict_to_query(request_params))
        self._request.setUrl(request_url)

        self._prepare_ssl()
        self._prepare_headers(request_headers)

        if not self.allow_redirects:
            session.manager.setRedirectPolicy(QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)

        if self.proxies is not None:
            for protocol, proxy_url in self.proxies.items():
                proxy_type: QNetworkProxy.ProxyType
                match protocol:
                    case '':
                        proxy_type = QNetworkProxy.ProxyType.NoProxy
                    case 'ftp':
                        proxy_type = QNetworkProxy.ProxyType.FtpCachingProxy
                    case 'http':
                        proxy_type = QNetworkProxy.ProxyType.HttpProxy
                    case 'socks5':
                        proxy_type = QNetworkProxy.ProxyType.Socks5Proxy
                    case other:
                        raise ValueError(f'proxy protocol "{other}" is not supported.')

                proxy_url = QUrl(proxy_url)
                proxy = QNetworkProxy(proxy_type, proxy_url.host(), proxy_url.port())
                session.manager.setProxy(proxy)

        if self.timeout:
            # Set transfer timeout amount
            # This is for the REQUEST side of the connection.
            transfer_timeout = int((self.timeout[1] if isinstance(self.timeout, Sequence) else self.timeout) * 1000)
            self._request.setTransferTimeout(transfer_timeout)

        verb: bytes = self.method.encode('utf8')
        _reply: QNetworkReply = session.manager.sendCustomRequest(self._request, verb, request_data)
        response: Response = self._prepare_response(_reply, finished, progress)

        if self.auth:
            session.reply_auth_map[_reply] = self.auth

        if session.manager.redirectPolicy() != session.default_redirect_policy:
            session.manager.setRedirectPolicy(session.default_redirect_policy)

        if wait_until_finished:
            wait_for_reply(_reply)

        return response


class Response:
    """``requests``-like wrapper over a :py:class:`QNetworkReply`."""

    def __init__(self, request: Request, reply: QNetworkReply) -> None:
        """Initialize the :py:class:`Response`."""
        self._data: bytes | None = None
        self._encoding: str | None = None
        self._headers: CaseInsensitiveDict = CaseInsensitiveDict()
        self._reply: QNetworkReply = reply
        self.request: Request = request

    def __del__(self) -> None:
        """Usually the last reference to this :py:class:`Response` is connected to a :py:class:`QNetworkReply` signal.

        So, when the :py:class:`QNetworkReply` is deleted using ``Response.delete()``, ``__del__`` is usually called.
        If this is not the case, and the :py:class:`QNetworkReply` was not yet deleted,
        delete it now to prevent a possible memory leak.
        """
        if Shiboken.isValid(self._reply):
            self._reply.deleteLater()

    def __repr__(self) -> str:
        """Representation of the :py:class:`Response` with its HTTP status code."""
        return f'<Response [{self.code}]>'

    @property
    def code(self) -> int | None:
        """Return the HTTP status code of the :py:class:`Response`.

        ``None`` is returned if the Request is not finished or has been aborted.
        """
        return self._reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)

    @property
    def data(self) -> bytes:
        """Return the :py:class:`Response` data as ``bytes``, and cache it for later use."""
        if self._data is None:
            self._data = self._reply.readAll().data()

        return self._data

    @property
    def encoding(self) -> str | None:
        """Return the detected encoding for data, and cache it for later use."""
        if self._encoding is None:
            decoder: QStringDecoder = QStringDecoder.decoderForHtml(self.data)
            self._encoding = str(decoder.name())

        return self._encoding

    @property
    def finished(self) -> bool:
        """Return whether the internal :py:class:`QNetworkReply` is marked as finished."""
        return self._reply.isFinished()

    @property
    def headers(self) -> CaseInsensitiveDict:
        """Return a :py:class:`CaseInsensitiveDict` containing the :py:class:`Response`'s HTTP headers."""
        # Assume that headers don't change after being set.
        if self._headers:
            return self._headers

        # Update with known headers
        for name, (enum_value, _) in KNOWN_HEADERS.lower_items():
            if (value := self._reply.header(enum_value)) is not None:
                self._headers[name] = value

        # Update with raw headers
        for raw_name, raw_value in self._reply.rawHeaderPairs():
            if (name := raw_name.toStdString()) not in self._headers:
                value: bool | int | str
                string_val: str = raw_value.toStdString()

                if string_val.lower() == 'true':
                    value = True

                elif string_val.lower() == 'false':
                    value = False

                elif match := _INT_PATTERN.match(string_val):
                    value = int(match[0])

                else:
                    value = string_val

                self._headers[name] = value

        return self._headers

    @property
    def json(self) -> dict[str, Any]:
        """Return the :py:class:`Response` data as a ``JSON`` object."""
        data: bytes = self.data
        if (encoding := self.encoding) is None:
            encoding = guess_json_utf(data) or 'utf8'

        return json_.loads(data.decode(encoding=encoding))

    @property
    def ok(self) -> bool:
        """Return whether ``self.code`` is a non-error code."""
        if self.code is None:
            return False

        return not is_error_status(self.code)

    @property
    def text(self) -> str:
        """Return the :py:class:`Response` data as a unicode-encoded string."""
        data: bytes = self.data
        encoding: str = self.encoding or 'utf8'

        if not data:
            return ''

        return data.decode(encoding=encoding)

    @property
    def url(self) -> QUrl:
        """Return the URL the :py:class:`Response` is from."""
        return self._reply.url()

    def delete(self) -> None:
        """Delete internal :py:class:`QNetworkReply`.

        If this :py:class:`Response` was connected to a signal which doesn't delete after call (such as progress),
        you will have to call this method before the :py:class:`Response` can be garbage collected.
        """
        self._reply.deleteLater()


_ResponseConsumer: TypeAlias = Callable[[Response], None]
_ProgressConsumer: TypeAlias = Callable[[Response, int, int], None]
