#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from dataclasses import MISSING, Field
from io import SEEK_CUR, SEEK_SET, BytesIO
from typing import Any, Callable, Dict, Optional, Tuple, Type

from .context import Context
from .types import (
    Adapter,
    AdapterType,
    Eval,
    FieldType,
    FormatType,
    Hook,
    HookType,
    T,
    Value,
)
from .utils.context import evaluate
from .utils.fields import build_field, build_wrapper, field_get_meta


def field(fmt: FormatType, *, default=..., default_factory=MISSING):
    return build_field(
        ftype=FieldType.FIELD,
        default=default,
        default_factory=default_factory,
        # meta
        fmt=fmt,
    )


def subfield(*, default_factory=MISSING):
    # don't allow 'default' for subfields, as they're always mutable
    return build_field(
        ftype=FieldType.FIELD,
        default_factory=default_factory,
        # meta
    )


def built(fmt: FormatType, builder: Value[Any], *, always: bool = True):
    return build_field(
        ftype=FieldType.FIELD,
        # meta
        fmt=fmt,
        builder=builder,
        always=always,
    )


def seek(offset: Value[int], *, absolute: bool = False):
    return build_field(
        ftype=FieldType.SEEK,
        public=False,
        # meta
        offset=offset,
        whence=SEEK_SET,
        absolute=absolute,
    )


def skip(offset: Value[int]):
    return build_field(
        ftype=FieldType.SEEK,
        public=False,
        # meta
        offset=offset,
        whence=SEEK_CUR,
    )


def padding(length: Value[int], *, pattern: bytes = None, check: bool = None):
    return build_field(
        ftype=FieldType.PADDING,
        public=False,
        # meta
        length=length,
        pattern=pattern,
        check=check,
    )


def align(
    modulus: Value[int],
    absolute: bool = False,
    *,
    pattern: bytes = None,
    check: bool = False,
):
    return build_field(
        ftype=FieldType.PADDING,
        public=False,
        # meta
        modulus=modulus,
        absolute=absolute,
        pattern=pattern,
        check=check,
    )


def action(_action: Eval[Any], /):
    return build_field(
        ftype=FieldType.ACTION,
        public=False,
        # meta
        action=_action,
    )


def hook(
    _hook: Hook = None,
    /,
    *,
    init: Eval[None] = None,
    update: HookType = None,
    read: HookType = None,
    write: HookType = None,
    end: Eval[None] = None,
):
    if [_hook, init or update or read or write or end].count(None) != 1:
        raise ValueError("Either 'hook' or at least one inline lambda has to be set")
    if not _hook:
        _hook = Hook()
        _hook.init = init
        _hook.update = update
        _hook.read = read
        _hook.write = write
        _hook.end = end
    return build_field(
        ftype=FieldType.HOOK,
        public=False,
        # meta
        hook=_hook,
    )


def hook_end():
    return build_field(FieldType.HOOK, public=False, hook=None)


def repeat(
    count: Value[int] = None,
    *,
    when: Eval[bool] = None,
    last: Eval[bool] = None,
    default_factory: Any = MISSING,
):
    if [count, when, last].count(None) == 3:
        raise ValueError("At least one of 'count', 'when' or 'last' has to be set")

    return build_wrapper(
        ftype=FieldType.REPEAT,
        default=...,
        default_factory=default_factory,
        # meta
        count=count,
        when=when,
        last=last,
    )


def cond(condition: Value[bool], *, if_not: Value[Any] = ...):
    return build_wrapper(
        ftype=FieldType.COND,
        # meta
        condition=condition,
        if_not=if_not,
    )


def switch(key: Value[Any]):
    def wrap(fields: Dict[Any, Tuple[Type, Field]] = None, **kwargs):
        fields = fields or {}
        fields.update(kwargs)
        return build_field(
            ftype=FieldType.SWITCH,
            # meta
            key=key,
            fields=fields,
        )

    return wrap


def adapter(
    _adapter: Adapter = None,
    /,
    *,
    encode: AdapterType = None,
    decode: AdapterType = None,
):
    if [_adapter, encode and decode].count(None) != 1:
        raise ValueError("Either 'adapter' or 'encode' and 'decode' has to be set")
    if not _adapter:
        _adapter = Adapter()
        _adapter.encode = encode
        _adapter.decode = decode

    def wrap(base: Field):
        meta = field_get_meta(base)
        if meta.ftype != FieldType.FIELD:
            raise TypeError("Can't assign adapters to non-standard fields")
        meta.adapter = _adapter
        return base

    return wrap


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


def buffer_hook(end: Callable[[BytesIO, Context], None]):
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
