#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from io import SEEK_CUR, SEEK_SET
from typing import IO

from ..types import Context, V, Value


def evaluate(ctx: Context, v: Value[V]) -> V:
    value: V = v
    if callable(v):
        # print("Evaluating with ctx:", ctx)
        value = v(ctx)
        return value
    return value


def build_context(parent: Context, io: IO[bytes], **values) -> Context:
    # create a context with some helpers and passed 'values' (from self)
    io_offset = io.tell()
    ctx = Context(**values)
    special = dict(
        _=parent,
        io=io,
        # tell the current position, relative to struct start
        tell=lambda: io.tell() - io_offset,
        # seek to a position, relative to struct start
        seek=lambda offset, whence=SEEK_SET: io.seek(offset + io_offset, whence),
        # skip a number of bytes
        skip=lambda length: io.seek(length, SEEK_CUR),
        # tell the current position, relative to IO start
        abstell=lambda: io.tell(),
        # seek to a position, relative to IO start
        absseek=lambda offset, whence=SEEK_SET: io.seek(offset, whence),
    )
    ctx.update(special)
    return ctx
