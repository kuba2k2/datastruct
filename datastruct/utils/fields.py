#  Copyright (c) Kuba Szczodrzyński 2023-1-6.

from dataclasses import MISSING, Field, is_dataclass
from enum import Enum
from io import SEEK_CUR
from typing import Any, Optional, Tuple

from ..context import Context
from ..types import Config, FieldMeta, FieldType
from .const import ARRAYS
from .context import evaluate
from .fmt import fmt_check
from .misc import pad_up, repstr


def field_encode(v: Any) -> Any:
    if isinstance(v, str):
        return v.encode()
    if isinstance(v, int):
        return v
    if isinstance(v, Enum):
        return v.value
    return v


def field_decode(v: Any, cls: type) -> Any:
    if issubclass(cls, str):
        return v.decode()
    if issubclass(cls, Enum):
        return cls(v)
    return v


def field_get_type(field: Field) -> Tuple[type, Optional[type]]:
    field_type = field.type
    if field_type is Ellipsis:
        return field_type, None
    if hasattr(field_type, "__origin__"):
        field_type = field.type.__origin__
    if not isinstance(field_type, type):
        return field_type, None
    if issubclass(field_type, ARRAYS) and hasattr(field.type, "__args__"):
        return field_type, field.type.__args__[0]
    return field_type, None


def field_get_meta(field: Field) -> FieldMeta:
    if callable(field.default):
        raise ValueError(
            f"Field '{field.name}' is most likely a wrapper field; "
            f"make sure to invoke it, passing base field as an argument",
        )
    if (
        isinstance(field.default, tuple)
        and field.default
        and isinstance(field.default[0], Field)
    ):
        raise TypeError(
            f"Field '{field.name}' default value is a tuple; "
            f"make sure you didn't add a comma after field declaration",
        )
    if not field.metadata:
        raise ValueError(
            f"Can't find field metadata of '{field.name}'; "
            f"use datastruct.field() instead of dataclass.field(); "
            f"remember to invoke wrapper fields (i.e. repeat()(), cond()()) "
            f"passing the base field in the parameters",
        )
    return field.metadata["datastruct"]


def field_get_base(meta: FieldMeta) -> Tuple[Field, FieldMeta]:
    return meta.base, field_get_meta(meta.base)


def field_do_seek(ctx: Context, meta: FieldMeta) -> None:
    offset = evaluate(ctx, meta.offset)
    if meta.whence == SEEK_CUR or meta.absolute:
        ctx.G.seek(offset, meta.whence)
    else:
        ctx.P.seek(offset, meta.whence)


def field_get_padding(
    config: Config,
    ctx: Context,
    meta: FieldMeta,
) -> Tuple[int, bytes, bool]:
    if meta.length:
        length = evaluate(ctx, meta.length)
    elif meta.modulus:
        modulus = evaluate(ctx, meta.modulus)
        tell = ctx.G.tell() if meta.absolute else ctx.P.tell()
        length = pad_up(tell, modulus)
    elif meta.offset:
        offset = evaluate(ctx, meta.offset)
        tell = ctx.G.tell() if meta.absolute else ctx.P.tell()
        if offset < tell:
            raise ValueError("Padding offset less than current tell() offset")
        length = offset - tell
    else:
        raise ValueError("Unknown padding type")
    if ctx.G.sizing:
        return length, b"", False
    check = meta.check if meta.check is not None else config.padding_check
    pattern = meta.pattern if meta.pattern is not None else config.padding_pattern
    return length, repstr(pattern, length), check


def field_switch_base(config: Config, ctx: Context, meta: FieldMeta) -> Field:
    key = evaluate(ctx, meta.key)
    keys = [key]
    if isinstance(key, int):
        keys.append(f"_{key}")
    if isinstance(key, bool):
        keys.append(str(key).lower())
    if isinstance(key, Enum):
        keys.append(key.name)
        keys.append(key.value)
    for key in keys:
        if key not in meta.fields:
            continue
        return meta.fields[key][1]
    if "default" in meta.fields:
        return meta.fields["default"][1]
    raise ValueError(f"Unmapped field type (and no default=...), tried {keys}")


def field_get_default(field: Field, meta: FieldMeta, ds: type) -> Any:
    if meta.ftype == FieldType.FIELD:
        if meta.builder:
            return Ellipsis
        # do what @dataclass would normally do - this is needed
        # for wrapper fields that are not REPEAT
        if field.default is not Ellipsis:
            return field.default
        if field.default_factory is not MISSING:
            return field.default_factory()
        if issubclass(field.type, ds):
            # try to initialize single fields with an empty object
            # noinspection PyArgumentList
            return field.type()
        return None

    # create lists for repeat() fields
    if meta.ftype == FieldType.REPEAT:
        # no need to care about 'default_factory' of 'field' here,
        # because @dataclass already sets that default value
        if isinstance(meta.count, int):
            # (try to) build a list of default/empty items
            items = []
            for _ in range(meta.count):
                if meta.base.default_factory is not MISSING:
                    items.append(meta.base.default_factory())
                elif meta.base.default is not Ellipsis:
                    items.append(meta.base.default)
                else:
                    items.append(meta.base.type())
            return field.type(items)
        else:
            # build an empty list for variable-length subfields
            # (when 'count' can't be determined at init-time)
            return []

    # extract single-field wrappers
    if meta.ftype == FieldType.COND:
        field, meta = field_get_base(meta)
        return field_get_default(field, meta, ds)

    # can't build a default value for switch fields
    if meta.ftype == FieldType.SWITCH:
        return Ellipsis

    return None


def field_validate(field: Field, meta: FieldMeta) -> None:
    if meta.validated:
        return
    field_type, item_type = field_get_type(field)

    # skip special fields (seek, padding, etc)
    if not meta.public:
        if field_type is not Ellipsis:
            raise TypeError("Use Ellipsis (...) for special fields")
        return
    if field_type is Ellipsis:
        raise TypeError("Cannot use Ellipsis for standard fields")

    # check some known type constraints
    if meta.ftype == FieldType.FIELD:
        if item_type is not None:
            # var: List[...] = field(...)
            raise ValueError("Can't use a list without repeat() wrapper")
        if is_dataclass(field_type) and meta.fmt and not meta.adapter:
            # var: DataStruct = field(...)
            raise ValueError("Use subfield() for instances of DataStruct")
        if meta.fmt:
            # validate format specifiers
            fmt_check(meta.fmt)

    elif meta.ftype == FieldType.REPEAT:
        base_field, base_meta = field_get_base(meta)
        if item_type is None:
            # var: ... = repeat()(...)
            raise ValueError("Can't use repeat() for a non-list field")
        if base_meta.ftype != FieldType.FIELD:
            # var: ... = repeat()(padding(...))
            raise ValueError(
                "Only field(), subfield() and built() can be used with repeat()"
            )
        if base_meta.builder and not base_meta.always:
            # var: ... = repeat()(built(..., always=False))
            raise ValueError("Built fields inside repeat() are always built")

    elif meta.ftype == FieldType.SWITCH:
        # test each case of the switch field
        for field_type, base_field in meta.fields.values():
            base_meta = field_get_meta(base_field)
            base_field.name = field.name
            base_field.type = field_type
            field_validate(base_field, base_meta)

    # update types and validate base fields
    if meta.base:
        base_field, base_meta = field_get_base(meta)
        base_field.name = field.name
        base_field.type = field.type
        if meta.ftype == FieldType.REPEAT:
            # "unwrap" item types for repeat fields only
            field.type = field_type
            base_field.type = item_type or field_type
        field_validate(base_field, base_meta)
    meta.validated = True
