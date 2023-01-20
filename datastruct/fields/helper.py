#  Copyright (c) Kuba Szczodrzyński 2023-1-7.

import dataclasses
from dataclasses import Field, is_dataclass
from io import BytesIO
from typing import Any, Callable, Optional, Type, Union

from ..context import Context
from ..types import Adapter, Eval, FieldMeta, FieldType, Hook, T, Value
from ..utils.context import evaluate
from ._utils import build_field
from .special import action, hook
from .standard import built, field
from .wrapper import adapter


def hook_end(hook: Field):
    meta: FieldMeta = hook.metadata["datastruct"]
    return build_field(
        ftype=FieldType.HOOK,
        public=False,
        # meta
        hook=meta.hook,
        end=True,
    )


def packing(check: Value[T]) -> Eval[T]:
    return lambda ctx: check(ctx) if ctx.G.packing and not ctx.G.sizing else None


def unpacking(check: Value[T]) -> Eval[T]:
    return lambda ctx: check(ctx) if ctx.G.unpacking else None


def virtual(value: Value[T]):
    return adapter(
        encode=lambda v, ctx: b"",
        decode=lambda v, ctx: evaluate(ctx, value),
    )(built(0, builder=value, always=True))


def tell():
    return virtual(lambda ctx: ctx.G.tell())


def tell_into(into: str):
    return action(lambda ctx: setattr(ctx, into, ctx.G.tell()))


def const_into(into: str, value: Any):
    return action(lambda ctx: setattr(ctx, into, value))


def eval_into(into: str, value: Value[Any]):
    return action(lambda ctx: setattr(ctx, into, evaluate(ctx, value)))


def probe():
    def _probe(ctx: Context):
        print(f"Probe: {ctx}")

    return action(_probe)


def validate(check: Eval[bool], doc: str = None):
    def _validate(ctx: Context):
        if not check(ctx):
            if not doc:
                raise ValueError(f"Validation failed; ctx={ctx}")
            raise ValueError(f"Validation failed at '{doc}'; ctx={ctx}")

    return action(_validate)


def buffer_start(end: Callable[[BytesIO, Context], None]):
    class Buffer(Hook):
        io: BytesIO

        def init(self, ctx: Context) -> None:
            self.io = BytesIO()

        def update(self, value: bytes, ctx: Context) -> Optional[bytes]:
            self.io.write(value)
            return value

        def end(self, ctx: Context) -> None:
            end(self.io, ctx)

    return hook(Buffer())


def buffer_end(buffer: Field):
    return hook_end(buffer)


def checksum_start(
    init: Callable[[Context], T],
    update: Callable[[bytes, T, Context], Optional[T]],
    end: Callable[[T, Context], Any],
):
    class Checksum(Hook):
        obj: T

        def init(self, ctx: Context) -> None:
            self.obj = init(ctx)

        def update(self, value: bytes, ctx: Context) -> Optional[bytes]:
            ret = update(value, self.obj, ctx)
            if ret is not None:
                self.obj = ret
            return value

        def end(self, ctx: Context) -> None:
            ctx.P.hook_checksum = end(self.obj, ctx)

    return hook(Checksum())


def checksum_end(checksum: Field):
    return hook_end(checksum)


def checksum_field(doc: str):
    class Checksum(Adapter):
        def encode(self, value: Any, ctx: Context) -> Any:
            if "hook_checksum" not in ctx.P:
                raise ValueError("Add a checksum_end() field first")
            # writing - return the valid checksum
            return ctx.P.hook_checksum

        def decode(self, value: Any, ctx: Context) -> Any:
            if "hook_checksum" not in ctx.P:
                raise ValueError("Add a checksum_end() field first")
            # reading - validate the checksum
            if value != ctx.P.hook_checksum:
                message = f"read {value}; calculated {ctx.P.hook_checksum}"
                if not doc:
                    raise ValueError(f"Checksum invalid; {message}")
                raise ValueError(f"Checksum invalid at '{doc}'; {message}")
            return value

    def wrap(base: Field):
        return adapter(Checksum())(base)

    return wrap


def bitfield(fmt: str, cls: Type[T], default: Union[bytes, int, None] = None):
    try:
        import bitstruct
    except (ModuleNotFoundError, ImportError):
        raise ImportError(
            "'bitstruct' package is not found, but required for bitfield()"
        )
    if not is_dataclass(cls):
        raise TypeError("'cls' must be a dataclass")
    size = bitstruct.calcsize(fmt) // 8
    if isinstance(default, int):
        default = default.to_bytes(length=size, byteorder="little")

    def encode(value: T, *_) -> bytes:
        data = dataclasses.astuple(value)
        return bitstruct.pack(fmt, *data)

    def decode(value: bytes, *_) -> T:
        data = bitstruct.unpack(fmt, value)
        return cls(*data)

    return adapter(encode=encode, decode=decode)(
        field(
            size,
            default_factory=lambda: decode(default),
        )
    )
