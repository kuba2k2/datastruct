#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from dataclasses import Field
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar, Union

from .context import Container, Context

T = TypeVar("T")

V = TypeVar("V")
Eval = Callable[[Context], V]
Value = Union[Eval[V], V]
FormatType = Value[Union[str, int]]
AdapterType = Callable[[Any, Context], Any]
HookType = Callable[[bytes, Context], Optional[bytes]]


class Adapter:
    # fmt: off
    def encode(self, value: Any, ctx: Context) -> Any: ...
    def decode(self, value: Any, ctx: Context) -> Any: ...
    # fmt: on


class Hook:
    # fmt: off
    def init(self, ctx: Context) -> None: ...
    def update(self, value: bytes, ctx: Context) -> Optional[bytes]: ...
    def read(self, value: bytes, ctx: Context) -> Optional[bytes]: ...
    def write(self, value: bytes, ctx: Context) -> Optional[bytes]: ...
    def end(self, ctx: Context) -> None: ...
    # fmt: on


class FieldType(Enum):
    # standard fields
    FIELD = auto()  # field(), subfield(), built(), adapter()
    # special fields
    SEEK = auto()  # seek(), skip()
    PADDING = auto()  # padding(), align()
    ACTION = auto()  # action()
    HOOK = auto()  # hook()
    # wrapper fields
    REPEAT = auto()  # repeat()
    COND = auto()  # cond()
    SWITCH = auto()  # switch()


class FieldMeta(Container):
    validated: bool
    public: bool
    ftype: FieldType
    # FIELD
    fmt: FormatType
    builder: Value[Any]
    always: bool
    adapter: Adapter
    kwargs: dict
    # SEEK
    offset: Value[int]
    whence: int
    absolute: bool
    # PADDING
    length: Value[int]
    modulus: Value[int]
    pattern: bytes
    check: bool
    # ACTION
    action: Eval[Any]
    # HOOK
    hook: Union[Hook, str]
    end: bool
    # REPEAT
    base: Field
    count: Value[int]
    when: Eval[bool]
    last: Eval[bool]
    # COND
    condition: Value[bool]
    if_not: Value[Any]
    # SWITCH
    key: Value[Any]
    fields: Dict[Any, Tuple[Type, Field]]


class Endianness(Enum):
    DEFAULT = "@"
    NATIVE = "="
    LITTLE = "<"
    BIG = ">"
    NETWORK = "!"


DEFAULT = Endianness.DEFAULT
NATIVE = Endianness.NATIVE
LITTLE = Endianness.LITTLE
BIG = Endianness.BIG
NETWORK = Endianness.NETWORK


class Config(Container):
    endianness: Endianness
    padding_pattern: bytes
    padding_check: bool
    repeat_fill: bool
