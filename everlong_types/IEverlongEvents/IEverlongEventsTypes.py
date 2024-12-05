"""Dataclasses for all structs in the IEverlongEvents contract.

DO NOT EDIT.  This file was generated by pypechain v0.0.48.
See documentation at https://github.com/delvtech/pypechain """

# super() call methods are generic, while our version adds values & types
# pylint: disable=arguments-differ

# contracts have PascalCase names
# pylint: disable=invalid-name

# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments

# unable to determine which imports will be used in the generated code
# pylint: disable=unused-import

# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return

# We import this contract itself to ensure all nested structs have a fully qualified name.
# We use this to avoid namespace collisions, as well as having a uniform
# type structure to do lookups when functions return these structs.
# pylint: disable=import-self


from __future__ import annotations

from dataclasses import dataclass

from pypechain.core import BaseEvent, BaseEventArgs


@dataclass(kw_only=True)
class PositionClosedEvent(BaseEvent):
    """The event type for event PositionClosed"""

    @dataclass(kw_only=True)
    class PositionClosedEventArgs(BaseEventArgs):
        """The args to the event PositionClosed"""

        maturityTime: int
        bondAmount: int

    # We redefine the args field with the specific event arg type.
    args: PositionClosedEventArgs  # type: ignore[override]

    __name__: str = "PositionClosed"


@dataclass(kw_only=True)
class PositionOpenedEvent(BaseEvent):
    """The event type for event PositionOpened"""

    @dataclass(kw_only=True)
    class PositionOpenedEventArgs(BaseEventArgs):
        """The args to the event PositionOpened"""

        maturityTime: int
        bondAmount: int

    # We redefine the args field with the specific event arg type.
    args: PositionOpenedEventArgs  # type: ignore[override]

    __name__: str = "PositionOpened"
