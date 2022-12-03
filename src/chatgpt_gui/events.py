###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################
"""Module used for Event subscription."""
from __future__ import annotations

__all__ = (
    'Event',
    'EventBus',
)

from collections import defaultdict
from collections.abc import Callable
from typing import Generic
from typing import overload
from typing import TypeAlias
from typing import TypeVar

from .utils import get_parent_doc


class Event:
    """Normal event with no special abilities.

    You can also use the >> operator to fire an :py:class:`Event` on an :py:class:`EventBus`. Ex::

        Event() >> EventBus['foo']
    """

    __slots__: tuple[str, ...] = ()

    def __repr__(self) -> str:
        """Representation of the :py:class:`Event` with its attributes' values."""
        values = {attr: getattr(self, attr) for attr in self.__slots__}
        return f'<"{self.name}" Event {values=}>' if self.__slots__ else f'<Empty {self.name}>'

    def __rshift__(self, __bus: EventBus, /) -> None:
        """Syntax sugar for __bus.fire(event)."""
        return __bus.fire(event=self)

    def __rlshift__(self, __bus: EventBus, /) -> None:
        """Right shift if the EventBus.__lshift__ dunder is not working."""
        return self >> __bus

    @property
    def name(self) -> str:
        """Name of event.

        Defaults to class name.
        """
        return type(self).__name__

    @property
    def description(self) -> str:
        """Short description of the event.

        Defaults to the first line of the nearest type doc in the mro.
        """
        doc: str | None = self.__doc__
        # pylint: disable=unidiomatic-typecheck
        if doc is None and isinstance(self, Event) and type(self) is not Event:
            doc = get_parent_doc(type(self))
        return doc.splitlines()[0] if doc is not None else ''


_ET = TypeVar('_ET', bound=Event)  # Bound to Event. Can use Event subclass instances in place of Event instances.
_EventPredicate: TypeAlias = Callable[[_ET], bool]
_EventRunnable: TypeAlias = Callable[[_ET], None]


class _Subscribers(defaultdict[type[Event], list[tuple[
    _EventRunnable,          # Callable to run
    _EventPredicate | None   # Optional predicate to run callable
]]], Generic[_ET]):
    """Class which holds the event subscribers for an :py:class:`EventBus`."""

    def __init__(self) -> None:
        super().__init__(list)

    def __repr__(self) -> str:
        """Amount of subscribers for every event, encased in parentheses."""
        repr_: str = ''
        for event in self:
            repr_ += f'{event.__name__}[{len(self[event])}], '
        return f'({repr_.rstrip(", ")})'

    def add(self,
            event: type[_ET],
            callable_pair:
            tuple[_EventRunnable, _EventPredicate | None]
            ) -> None:
        """Add a callable pair to an Event subscriber list.

        :raises TypeError:
            If event is not a subclass of Event.
            If subscriber is not callable.
            If subscriber's predicate is defined but not a callable.
        """
        if not issubclass(event, Event):
            raise TypeError(f'event is not subclass to {Event}.')
        if not callable(callable_pair[0]):
            raise TypeError('subscriber is not callable.')
        if callable_pair[1] is not None and not callable(callable_pair[1]):
            raise TypeError('subscriber predicate is defined but not callable.')

        self[event].append(callable_pair)


class _EventBusMeta(type):
    """Metaclass for :py:class:`EventBus` type.

    Maps :py:class:`EventBus` objects to :py:class:`str` ids
    and allows accessing those ids using subscripts on :py:class:`EventBus`.
    """

    _id_bus_map: dict[str, EventBus] = {}

    @overload
    def __getitem__(cls, id: type[Event]) -> type[EventBus]:
        # FOR TYPE HINTING, IGNORE
        ...

    @overload
    def __getitem__(cls, id: str) -> EventBus:
        ...

    # pylint: disable=comparison-of-constants, compare-to-zero, no-value-for-parameter
    def __getitem__(cls, id) -> EventBus | type[EventBus]:
        # FOR TYPE HINTING, IGNORE
        if True is False:
            if issubclass(id, Event):
                return cls  # type: ignore

        if (bus := cls.get_bus(id)) is None:
            raise KeyError(f'{cls.__name__} "{id}" does not exist.')

        return bus

    def __setitem__(cls, id: str, bus: EventBus) -> None:
        """Set an :py:class:`EventBus` from the bus map.

        :raises TypeError:
            If id is not a str.
            If bus is not an Eventbus.
        """
        if not isinstance(id, str):
            raise TypeError(f'parameter {id=} is not of type {str}.')
        if not isinstance(bus, EventBus):
            raise TypeError(f'parameter {bus=} is not of type {EventBus}.')

        if bus.id is None:
            bus.id = id

        cls._id_bus_map[id.lower()] = bus

    def __delitem__(cls, id: str) -> None:
        """Delete an :py:class:`EventBus` from the bus map."""
        del cls._id_bus_map[id.lower()]

    def get_bus(cls, id: str, default: EventBus | None = None) -> EventBus | None:
        """Get bus from class map using the given id, with an optional default value.

        :param id: Case-insensitive id to search with.
        :param default: Default value if id resolves to None.
        :return: EventBus mapped to given id.
        """
        return cls._id_bus_map.get(id.lower(), default)


class EventBus(Generic[_ET], metaclass=_EventBusMeta):
    """Object that keeps track of all :py:class:`Callable` subscriptions to :py:class:`Event`'s.

    An Event Bus is an event-driven structure that stores both events and functions. When an
    event is fired, all functions "subscribed" to the event or any of its parent events are called with
    the event as a parameter.

    All :py:class:`EventBus`'s are stored in the class with a unique id.
    You can access created :py:class:`EventBus`'s with subscripts. ex::

        [Python Interactive Prompt]
            EventBus['foo'] -> None
            EventBus('foo') -> EventBus object at 0x000000001
            EventBus['foo'] -> EventBus object at 0x000000001
            del EventBus['foo']
            EventBus['foo'] -> None

    You can also use the << operator to fire an event, or an Event's >> operator. ex::

        [Python Interactive Prompt]
            # These fire an event
            EventBus['foo'] << Event()
            Event() >> EventBus['foo']

            # This raises an error:
            Event() << EventBus['foo']
    """

    def __init__(self, __id: str | None = None, /) -> None:
        """Create a new :py:class:`EventBus` object with a unique id.

        All ids are transformed to lowercase in the :py:class:`_EventBusMeta` id map.

        :param __id: id to register this instance as.
        :raises KeyError: When a bus with the given id already exists.
        """
        if __id is not None and type(self).get_bus(__id) is not None:
            raise KeyError(f'EventBus id "{__id}" is already registered in {type(type(self)).__name__}')

        self.id: str | None = __id
        self._subscribers: _Subscribers = _Subscribers()

        if __id is not None:
            type(self)[__id] = self

    def __lshift__(self, __event: _ET | type[_ET], /) -> None:
        """Syntax sugar for self.fire(event)."""
        return self.fire(__event)

    def __repr__(self) -> str:
        """Representation of the :py:class:`EventBus` with its id and :py:class:`_Subscribers`."""
        return f'<{type(self).__name__} id={self.id!r}; Subscribers={self._subscribers!r}>'

    def clear(self, event: type[_ET] | None = None) -> None:
        """Clear event _subscribers of a given type.

        None is treated as a wildcard and deletes ALL event _subscribers.

        :param event: Event type to clear.
        """
        if event is None:
            self._subscribers.clear()
        else:
            self._subscribers.pop(event)

    def fire(self, event: _ET | type[_ET]) -> None:
        """Fire all :py:class:`Callables` subscribed to the :py:class:`Event`'s :py:class:`type`.

        :py:class:`Event` subclasses call their parent's callables as well.
        Ex: ChildEvent will fire ParentEvent, but ParentEvent will not fire ChildEvent.

        If event is a :py:class:`type`, it is instantiated with no arguments.

        :param event: Event object passed to callables as an argument.
        """
        # Transform Event types to their default instances
        if isinstance(event, type) and issubclass(event, Event):
            event = event()

        # Run all current and parent event callables
        for event_type in self._subscribers:
            if isinstance(event, event_type):
                for e_callable_pair in self._subscribers[event_type]:
                    # Check predicate if one is given
                    if e_callable_pair[1] is None or e_callable_pair[1](event):

                        # Finally, call
                        e_callable_pair[0](event)

    # pylint: disable=useless-param-doc
    def subscribe(self,
                  __callable: _EventRunnable, /,
                  event: type[_ET],
                  event_predicate: _EventPredicate | None = None
                  ) -> None:
        """Subscribe a :py:class:`Callable` to an :py:class:`Event` type.

        By default, every time an :py:class:`Event` is fired, it will call the callable with the event as an argument.

        :param __callable: Callable to run.
        :param event: Event to subscribe to.
        :param event_predicate: Predicate to validate before running callable.
        :raises TypeError: If the given arguments are not valid.
        """
        callable_pair = (__callable, event_predicate)
        self._subscribers.add(event, callable_pair)
