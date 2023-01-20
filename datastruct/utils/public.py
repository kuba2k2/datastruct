#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from typing import Optional, Sized

from ..context import Context
from ..main import DataStruct
from ..types import Endianness
from .const import ARRAYS


def datastruct(
    endianness: Endianness = None,
    padding_pattern: bytes = None,
    padding_check: bool = None,
    repeat_fill: bool = None,
):
    args = {k: v for k, v in locals().items() if v is not None}

    def wrap(cls):
        setattr(cls, "_CONFIG", args)
        return cls

    return wrap  # @datastruct(...)


def sizeof(o, ctx: Optional[Context] = None) -> int:
    if isinstance(o, DataStruct):
        return o.sizeof(parent=ctx)
    if isinstance(o, ARRAYS):
        return sum(i.sizeof(parent=ctx) for i in o)
    if isinstance(o, Sized):
        return len(o)
    raise TypeError(f"Unknown type '{type(o)}'")
