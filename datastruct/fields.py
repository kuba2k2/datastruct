#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from dataclasses import MISSING
from io import SEEK_CUR, SEEK_SET
from typing import Any

from .types import Eval, FieldType, FormatType, T, Value
from .utils.fields import build_field, build_wrapper


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
    absolute: bool,
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


def repeat(
    count: Value[int] = None,
    *,
    when: Eval[bool] = None,
    last: Eval[bool] = None,
    default_factory: Any = MISSING,
):
    if [count, when, last].count(None) < 1:
        raise ValueError("At least one of 'count', 'when' or 'last' has to be set")

    return build_wrapper(
        ftype=FieldType.REPEAT,
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


def packing(check: Value[T]) -> Eval[T]:
    return lambda ctx: check(ctx) if ctx.packing else None


def unpacking(check: Value[T]) -> Eval[T]:
    return lambda ctx: check(ctx) if ctx.unpacking else None
