#  Copyright (c) Kuba Szczodrzyński 2023-1-7.

from dataclasses import Field
from io import BytesIO
from typing import Any, Callable, Optional

from ..context import Context
from ..types import Adapter, Eval, FieldType, Hook, T, Value
from ..utils.context import evaluate
from ._utils import build_field
from .special import action, hook
from .standard import built
from .wrapper import adapter


def hook_end(name: str):
    return build_field(FieldType.HOOK, public=False, hook=name)


def packing(check: Value[T]) -> Eval[T]:
    return lambda ctx: check(ctx) if ctx.G.packing else None


def unpacking(check: Value[T]) -> Eval[T]:
    return lambda ctx: check(ctx) if ctx.G.unpacking else None


def virtual(value: Value[T]):
    return adapter(
        encode=lambda v, ctx: b"",
        decode=lambda v, ctx: evaluate(ctx, value),
    )(built(0, builder=value, always=True))


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

    return hook("hook_buffer", Buffer())


def buffer_end():
    return hook_end("hook_buffer")


def checksum_start(
    init: Callable[[], T],
    update: Callable[[bytes, T], Optional[T]],
    end: Callable[[T], Any],
):
    class Checksum(Hook):
        obj: T

        def init(self, ctx: Context) -> None:
            self.obj = init()

        def update(self, value: bytes, ctx: Context) -> Optional[bytes]:
            ret = update(value, self.obj)
            if ret is not None:
                self.obj = ret
            return value

        def end(self, ctx: Context) -> None:
            ctx.P.hook_checksum = end(self.obj)

    return hook("hook_checksum", Checksum())


def checksum_end():
    return hook_end("hook_checksum")


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
