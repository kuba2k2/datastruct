#  Copyright (c) Kuba Szczodrzyński 2023-1-7.

from dataclasses import Field
from io import SEEK_CUR, SEEK_SET
from typing import Any

from ..types import (
    Eval,
    FieldMeta,
    FieldType,
    Hook,
    HookType,
    IOHook,
    ReadType,
    SeekType,
    TellType,
    Value,
    WriteType,
)
from ._utils import build_field


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


def padding(
    length: Value[int],
    *,
    pattern: bytes = None,
    check: bool = None,
):
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
    check: bool = None,
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


def alignto(
    offset: Value[int],
    absolute: bool = False,
    *,
    pattern: bytes = None,
    check: bool = None,
):
    return build_field(
        ftype=FieldType.PADDING,
        public=False,
        # meta
        offset=offset,
        absolute=absolute,
        pattern=pattern,
        check=check,
    )


def action(_action: Eval[Any]):
    return build_field(
        ftype=FieldType.ACTION,
        public=False,
        # meta
        action=_action,
    )


def hook(
    _hook: Hook = None,
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
        end=False,
    )


def hook_end(hook_field: Field):
    meta: FieldMeta = hook_field.metadata["datastruct"]
    return build_field(
        ftype=FieldType.HOOK,
        public=False,
        # meta
        hook=meta.hook,
        end=True,
    )


def io(
    _io: IOHook = None,
    *,
    init: Eval[None] = None,
    read: ReadType = None,
    write: WriteType = None,
    seek: SeekType = None,
    tell: TellType = None,
    end: Eval[None] = None,
):
    if [_io, init or read or write or seek or tell or end].count(None) != 1:
        raise ValueError("Either 'io' or at least one inline lambda has to be set")
    if not _io:
        _io = Hook()
        _io.init = init or _io.init
        _io.read = read or _io.read
        _io.write = write or _io.write
        _io.seek = seek or _io.seek
        _io.tell = tell or _io.tell
        _io.end = end or _io.end
    return build_field(
        ftype=FieldType.IO,
        public=False,
        # meta
        io=_io,
        end=False,
    )


def io_end(io_field: Field):
    meta: FieldMeta = io_field.metadata["datastruct"]
    return build_field(
        ftype=FieldType.IO,
        public=False,
        # meta
        io=meta.io,
        end=True,
    )
