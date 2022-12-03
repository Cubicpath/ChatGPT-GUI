###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Miscellaneous objects for chatgpt_gui."""
from __future__ import annotations

__all__ = (
    'CaseInsensitiveDict',
    'DeferredCallable',
    'DistributedCallable',
    'Singleton',
)

import sys
import weakref
from abc import ABC
from abc import abstractmethod
from collections import OrderedDict
from collections.abc import Callable
from collections.abc import Collection
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import MutableMapping
from typing import Any
from typing import Generic
from typing import NoReturn
from typing import TypeAlias
from typing import TypeVar
from warnings import warn

_VT = TypeVar('_VT')
_CT = TypeVar('_CT', bound=Collection[Callable])  # Bound to Collection of Callables
_PT = TypeVar('_PT')  # Positional Arguments
_KT = TypeVar('_KT')  # Keyword Arguments
_PTCallable: TypeAlias = Callable[[], _PT]  # Which returns _PT
_KTCallable: TypeAlias = Callable[[], _KT]  # Which returns _KT


class _AbstractCallable(ABC):
    """Abstract :py:class:`Callable` object.

    Child objects are callable as a shortcut to their `run` method.
    """

    def __call__(self, *args, **kwargs) -> Any:
        """Syntax sugar for self.run()."""
        return self.run(*args, **kwargs)

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute functionality with the provided arguments and return the result.

        :param args: positional arguments to call with.
        :param kwargs: keyword arguments to call with.
        """
        raise NotImplementedError

##########
# NOTICE:
##########
# Requests
# Copyright 2019 Kenneth Reitz
# Apache 2.0 License
# https://github.com/psf/requests/blob/main/LICENSE


class CaseInsensitiveDict(MutableMapping, Generic[_VT]):
    """A case-insensitive :py:class:`dict`-like object.

    Implements all methods and operations of
    :py:class:`MutableMapping` as well as :py:class:`dict`'s ``copy``. Also
    provides ``lower_items``.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case-insensitive::

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.

    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """

    __slots__ = ('_store',)

    def __init__(self,
                 data: Iterable[tuple[str, _VT]] | Mapping[str, _VT] | None = None,
                 **kwargs
                 ) -> None:
        """Create a :py:class:`CaseInsensitiveDict` with the given data.

        :param data: Data to turn into a CaseInsensitiveDict
        :param kwargs: key-values in form of kwargs
        """
        self._store = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key: str, value: _VT) -> None:
        """Set the associated value of the given key.

        Use the lowercased key for lookups, but store the actual key alongside the value.
        """
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> _VT:
        """Get the associated value of the given key.

        Use the lowercased key for lookups.
        """
        return self._store[key.lower()][1]

    def __delitem__(self, key: str) -> None:
        """Delete the key and associated value from the dictionary."""
        del self._store[key.lower()]

    def __iter__(self) -> Generator[str, None, None]:
        """Return a :py:class:`Generator` containing all original (cased) keys."""
        return (cased_key for cased_key, mapped_value in self._store.values())

    def __len__(self) -> int:
        """Return amount of key-value pairs."""
        return len(self._store)

    def __or__(self, other: Mapping) -> CaseInsensitiveDict:
        """Update operator for :py:class:`Mapping`'s.

        :return: A new :py:class`CaseInsensitiveDict` with the updated pairs of this and the other :py:class:`Mapping`.
        """
        if not isinstance(other, Mapping):
            return NotImplemented

        new = self.__class__(self)
        new.update(other)
        return new

    def __ror__(self, other: Mapping) -> CaseInsensitiveDict:
        """Update operator for :py:class:`Mapping`'s that don't support the syntax.

        :return: A new :py:class`CaseInsensitiveDict` with the updated pairs of this and the other :py:class:`Mapping`.
        """
        if not isinstance(other, Mapping):
            return NotImplemented

        new = self.__class__(other)
        new.update(self)
        return new

    def __ior__(self, other: Mapping) -> CaseInsensitiveDict:
        """Update setter operator for :py:class:`Mapping`'s.

        :return: This :py:class`CaseInsensitiveDict` with the updated pairs of the other :py:class:`Mapping`.
        """
        self.update(other)

        return self

    def lower_items(self) -> Generator[tuple[str, _VT], None, None]:
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lower_key, keyval[1])
            for (lower_key, keyval)
            in self._store.items()
        )

    def __eq__(self, other: Mapping[str, _VT]) -> bool:
        """Compare items of other :py:class:`Mapping` case-insensitively."""
        if not isinstance(other, Mapping):
            return NotImplemented

        # Compare insensitively
        other_no_case: CaseInsensitiveDict[_VT] = self.__class__(other)
        return dict(self.lower_items()) == dict(other_no_case.lower_items())

    # Copy is required
    def copy(self) -> CaseInsensitiveDict[_VT]:
        """Return new :py:class:`CaseInsensitiveDict` with a copy of this instance's keys and values."""
        return self.__class__(self._store.values())

    def __repr__(self) -> str:
        """Representation of the :py:class:`CaseInsensitiveDict`."""
        return str(dict(self.items()))


class DeferredCallable(_AbstractCallable, Generic[_PT, _KT]):
    """A :py:class:`Callable` with args and kwargs stored for further execution.

    Supports deferred argument evaluation when using :py:class:`Callable`'s as arguments.
    This allows the value of the stored arguments to dynamically change depending on
    when the :py:class:`DeferredCallable` is executed.
    """

    __slots__ = ('_extra_pos_args', 'call_funcs', 'call_types', 'callable', 'args', 'kwargs')

    def __init__(self, __callable: Callable = lambda: None, /, *args: _PT | _PTCallable,
                 _extra_pos_args: int = 0,
                 _call_funcs: bool = True,
                 _call_types: bool = False,
                 **kwargs: _KT | _KTCallable) -> None:
        """Create a new :py:class:`DeferredCallable`.

        When called, any additional arguments must be expected with _extra_pos_args.
        Any arguments that exceed the extra positional argument limit will be trimmed off.

        :param __callable: Callable to store for later execution.
        :param args: positional arguments to store
        :param _extra_pos_args: Extra positional arguments to expect with self.run.
        :param _call_funcs: Whether to call (non-type) callable arguments
        :param _call_types: Whether to call class constructor arguments
        :param kwargs: keyword arguments to store
        """
        self._extra_pos_args: int = _extra_pos_args
        self.call_funcs: bool = _call_funcs
        self.call_types: bool = _call_types
        self.callable: Callable = __callable
        self.args: tuple[_PT | _PTCallable, ...] = args
        self.kwargs: dict[str, _KT | _KTCallable] = kwargs

    def __repr__(self) -> str:
        """Representation of the :py:class:`DeferredCallable` with the stored callable, args, and kwargs."""
        args, kwargs = self.args, self.kwargs
        return f'<{type(self).__name__} {self.callable} with {args=}, {kwargs=}>'

    def _evaluate_value(self, val: Any) -> Any:
        """Evaluate the given value to its called value if we want to know it.

        :param val: Value to evaluate.
        :return: The called value, if callable.
        """
        return val() if callable(val) and (
            (isinstance(val, type) and self.call_types) or
            (not isinstance(val, type) and self.call_funcs)
        ) else val

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the stored :py:class:`Callable`.

        Takes any additional arguments and temporarily adds to the stored arguments before execution.

        :param args: positional arguments to pass to callable.
        :param kwargs: keyword arguments to pass callable.
        :raises RuntimeError: Internal callable was not expecting the amount of positional arguments given.
        """
        # Add additional arguments from local args
        args = self.args + args[:self._extra_pos_args]  # Trim all arguments that are not expected
        kwargs |= self.kwargs

        # Evaluate all callable arguments
        args = tuple(self._evaluate_value(arg) for arg in args)
        kwargs = {key: self._evaluate_value(val) for key, val in kwargs.items()}

        try:
            return self.callable(*args, **kwargs)
        except TypeError as e:
            if ' positional argument but ' in str(e):
                raise RuntimeError(
                    f'{str(e).split(" ", maxsplit=1)[0]} was not expecting additional args, '
                    f'{type(self).__name__}._extra_call_args may not be set correctly.'
                ) from e


class DistributedCallable(_AbstractCallable, Generic[_CT, _PT, _KT]):
    """A :py:class:`Callable` that distributes arguments to all specified callables.

    Supports generic type hinting for the callable collections and arguments. Ex::

        foo: DistributedCallable[set] = DistributedCallable({bar}, 1, 2, 3, four=4)
        foo2: DistributedCallable[list] = DistributedCallable([bar], 1, 2, 3, four=4)

        # Now there's no error when doing

        foo.callables.add(baz)
        # And
        foo2.callables.append(baz)
    """

    __slots__ = ('callables', 'args', 'kwargs')

    def __init__(self, __callables: _CT = (), /, *args: _PT, **kwargs: _KT) -> None:
        """Create a new :py:class:`DistributedCallable` with the stored callables, args, and kwargs.

        _CT is a Type Generic containing a :py:class:`Collection` of callables.
        """
        self.callables: _CT = __callables
        self.args: tuple[_PT, ...] = args
        self.kwargs: dict[str, _KT] = kwargs

    def __repr__(self) -> str:
        """Representation of the :py:class:`DistributedCallable` with the stored callable, args, and kwargs."""
        args, kwargs = self.args, self.kwargs
        return f'<{type(self).__name__} {len(self.callables)} functions with {args=}, {kwargs=}>'

    def run(self, *args, **kwargs) -> tuple[Any, ...]:
        """Run all stored :py:class:`Callable`'s with the given extra arguments.

        :return: The results of each callable, packaged in a tuple.
        """
        results = tuple(func(*self.args, **self.kwargs) for func in self.callables)
        return results

    def generate(self, *args, **kwargs) -> Generator[Any, None, None]:
        """Run all stored :py:class:`Callable`'s with the given extra arguments. Yielding every result.

        :return: A generator yielding the results of each callable.
        """
        for func in self.callables:
            yield func(*args, **kwargs)


class Singleton:
    """A type which can only support one object instance at a time.

    All public "instances" of :py:class:`Singleton` are actually weakref proxies to
    the ``_Singleton__instance`` class attribute.

    DO:
        Anything with ``Singleton.instance()`` return value.

    DO NOT:
        Access ``_Singleton__instance`` class attribute outside the class.

        Store ``_Singleton__instance`` class attribute in any variable.

    -----

    When subclassing :py:class:`Singleton`, you must override the ``__init__`` abstract method.

    If you are subclassing multiple classes, it should always be the first in the order, and should specify the
    other class as your ``_singleton_base_type`` in your class definition. ex::

        class MySingleton(Singleton, OtherClass):
            _singleton_base_type = OtherClass
            _singleton_check_ref = True

            def __init__(self):
                ...

    If you are subclassing a C-Extension object (Such as a PySide ``QObject``) which keeps a hard-ref, or
    otherwise cannot guarantee the non-existence of outside references to the singleton instance, set the
    ``_singleton_check_ref`` attribute to ``False`` in your class definition.

    This removes all checks to the ``sys`` ref count.

    -----

    Create:
        To instantiate the :py:class:`Singleton` instance, use the ``create()`` class method.
        While instantiated,

        Attempting to use ``create()`` while the :py:class:`Singleton` is instantiated will
        raise a :py:class:`RuntimeError`.

    Access:
        You can access the :py:class:`Singleton` instance from the class definition by using the
        ``instance()`` class method.

        Attempting to use ``instance()`` before the :py:class:`Singleton` is created will
        raise a :py:class:`RuntimeError`.

        To check whether the :py:class:`Singleton` is instantiated, use the ``is_instantiated()`` class method.

    Destroy:
        :py:class:`Singleton` instances must be destroyed before you can create a new one. To do so,
        call the ``destroy()`` class method. Calling destroy guarantees that all references to the instance are
        deleted and garbage collected.

        If this isn't possible, and ``_singleton_check_ref`` is ``True``, a :py:class:`RuntimeError` is raised.

        Attempting to use ``destroy()`` before the :py:class:`Singleton` is created will
        raise a :py:class:`RuntimeError`.
    """

    __slots__: tuple[str, ...] = ()

    _singleton_base_type: type = object
    _singleton_check_ref: bool = True
    __instance: Singleton | None = None
    """The singular reference for the class instance. Should ONLY be accessed using weak reference proxies.

    Singleton.__instance is never used, all subclasses have their own __instance class attribute.
    """

    def __new__(cls, *args, **kwargs) -> NoReturn:
        """Call the :py:class:`Singleton`.create() classmethod instead.

        :raises TypeError: When called.
        """
        raise TypeError(
            f'Do not call default constructor for {cls.__name__}, instead call {cls.__name__}.create() explicitly.'
        )

    # pylint: disable=useless-super-delegation
    def __init__(self, *args, **kwargs) -> None:
        """Bare ``__init__`` used as placeholder.

        When replaced, its replacement is called by :py:class:`Singleton`.create()
        """
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, *args, **kwargs) -> None:
        """Ensure that the class instance is set to None for all subclasses."""
        super().__init_subclass__(*args, **kwargs)

        cls.__instance = None

    @classmethod
    def _check_ref_count(cls) -> bool:
        """Check if reference count is 1 for the :py:class:`Singleton` instance.

        Warns user if they access the internal instance.
        """
        if cls._singleton_check_ref:
            # 1 for cls.__instance, anymore is undefined behaviour. (Subtract 1 for argument reference)
            if cls.is_instantiated() and (sys.getrefcount(cls.__instance) - 1) > 1:
                warn(RuntimeWarning(
                    f'There is an outside reference to the internal {cls.__name__} instance. '
                    f'This is undefined behavior; please use weakref proxies.'
                ))
                return False

        return True

    @classmethod
    def create(cls, *args, **kwargs) -> None:
        """Preferred way of creating the :py:class:`Singleton` instance.

        :raises RuntimeError: If singleton instance currently exists.
        :raises TypeError: If __init__ is not overridden.
        """
        # All subclasses of Singleton should override __init__
        if cls.__init__ is Singleton.__init__:
            raise TypeError(
                f'Could not instantiate abstract class {cls.__name__} with abstract method __init__.'
            )

        if cls.is_instantiated():
            cls._check_ref_count()
            raise RuntimeError(
                f'Please destroy the {cls.__name__} singleton before creating a new {cls.__name__} instance.'
            )

        cls.__instance = cls._singleton_base_type.__new__(cls)  # type: ignore
        cls.__init__(cls.__instance, *args, **kwargs)

    @classmethod
    def instance(cls: type[_SingletonT]) -> _SingletonT:  # Real return type is weakref.ProxyType[Singleton]
        """Return a weak reference to the :py:class:`Singleton` instance.

        :raises RuntimeError: If singleton is not currently instantiated.
        """
        cls._check_ref_count()

        if not cls.is_instantiated():
            raise RuntimeError(
                f'Called {cls.__name__}.instance() when {cls.__name__} is not instantiated.'
            )

        return weakref.proxy(cls.__instance)

    @classmethod
    def destroy(cls) -> None:
        """Destroy the :py:class:`Singleton` instance.

        This results in the destruction of all weak references to the previous instance.

        :raises RuntimeError:
            If singleton instance could not be destroyed.
            If singleton is not currently instantiated.
        """
        if not cls._check_ref_count():
            raise RuntimeError(
                f'Could not destroy weak references to the {cls.__name__} instance. '
                f'Please remove all outside references to the internal instance before '
                f'calling {cls.__name__}.destroy().'
            )

        if not cls.is_instantiated():
            raise RuntimeError(
                f'Called {cls.__name__}.destroy() when {cls.__name__} is not instantiated.'
            )

        cls.__instance = None

    @classmethod
    def is_instantiated(cls) -> bool:
        """Return whether the :py:class:`Singleton` instance exists."""
        return isinstance(cls.__instance, cls)


_SingletonT = TypeVar('_SingletonT', bound=Singleton)
