#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from functools import partial
from io import SEEK_CUR, SEEK_SET
from typing import IO, Optional

from ..types import Config, Context, FieldMeta, V, Value


def evaluate(ctx: Context, v: Value[V]) -> V:
    value: V = v
    if callable(v):
        # print("Evaluating with ctx:", ctx)
        value = v(ctx)
        return value
    return value


def build_global_context(
    io: IO[bytes],
    packing: bool = False,
    unpacking: bool = False,
    sizing: bool = False,
) -> Context.Global:
    glob = Context.Global(
        io=io,
        io_hook=None,
        packing=packing,
        unpacking=unpacking,
        sizing=sizing,
        root=None,
        hooks=[],
        # tell the current position, relative to IO start
        tell=lambda: (glob.io_hook or glob.io).tell(),
        # seek to a position, relative to IO start
        seek=lambda offset, whence=SEEK_SET: (glob.io_hook or glob.io).seek(
            offset, whence
        ),
    )
    return glob


def build_context(
    glob: Context.Global,
    parent: Optional[Context],
    config: Config,
    **kwargs,
) -> Context:
    # create a context with some helpers and passed 'values' (from self)
    io_offset = (glob.io_hook or glob.io).tell()
    # build params container
    params = Context.Params(
        # current DataStruct's config
        config=config,
        # tell the current position, relative to struct start
        tell=lambda: (glob.io_hook or glob.io).tell() - io_offset,
        # seek to a position, relative to struct start
        seek=lambda offset, whence=SEEK_SET: (glob.io_hook or glob.io).seek(
            offset + (io_offset if whence == SEEK_SET else 0), whence
        ),
        # skip a number of bytes
        skip=lambda length: (glob.io_hook or glob.io).seek(length, SEEK_CUR),
        # context arguments
        kwargs=kwargs,
    )
    ctx = Context(_=parent, G=glob, P=params, **kwargs)
    # set this context as root, if not already set
    if glob.root is None:
        glob.root = ctx
    return ctx


def ctx_read(ctx: Context, n: int) -> bytes:
    if not n:
        return b""
    s = (ctx.G.io_hook or ctx.G.io).read(n)
    s = hook_do(ctx, "update", s)
    s = hook_do(ctx, "read", s)
    return s


def ctx_write(ctx: Context, s: bytes) -> int:
    if not s:
        return 0
    s = hook_do(ctx, "update", s)
    s = hook_do(ctx, "write", s)
    n = (ctx.G.io_hook or ctx.G.io).write(s)
    return n


def hook_apply(ctx: Context, meta: FieldMeta):
    hook = meta.hook
    if not meta.end:
        # add the hook to the list
        evaluate(ctx, hook.init)
        ctx.G.hooks.append(hook)
    else:
        # remove the hook
        ctx.G.hooks.remove(hook)
        evaluate(ctx, hook.end)


def hook_do(ctx: Context, action: str, data: V) -> V:
    for hook in ctx.G.hooks:
        func = getattr(hook, action, None)
        if not func:
            continue
        value = func(data, ctx)
        if value is None:
            continue
        data = value
    return data


def io_apply(ctx: Context, meta: FieldMeta):
    io = meta.io
    if not meta.end:
        if ctx.G.io_hook is not None:
            raise RuntimeError("IO hook already set")
        if isinstance(io.read, partial):
            raise RuntimeError("IO hook not ended - use io_end()")
        # set the IO hook
        evaluate(ctx, io.init)
        ctx.G.io_hook = io
        io.read = partial(io.read, ctx)
        io.write = partial(io.write, ctx)
        io.seek = partial(io.seek, ctx)
        io.tell = partial(io.tell, ctx)
    else:
        # remove the hook
        while isinstance(io.read, partial):
            io.read = io.read.func
        while isinstance(io.write, partial):
            io.write = io.write.func
        while isinstance(io.seek, partial):
            io.seek = io.seek.func
        while isinstance(io.tell, partial):
            io.tell = io.tell.func
        ctx.G.io_hook = None
        evaluate(ctx, io.end)
