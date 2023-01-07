#  Copyright (c) Kuba Szczodrzyński 2023-1-7.

from io import BytesIO
from typing import Callable, Optional

from ..context import Context
from ..types import Eval, FieldType, Hook, T, Value
from ..utils.context import evaluate
from ._utils import build_field
from .special import action, hook
from .standard import built
from .wrapper import adapter


def hook_end():
    return build_field(FieldType.HOOK, public=False, hook=None)


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


def buffer(end: Callable[[BytesIO, Context], None]):
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
