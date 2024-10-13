#  Copyright (c) Kuba Szczodrzyński 2023-1-6.

from dataclasses import MISSING, Field, is_dataclass
from enum import Enum
from io import SEEK_CUR
from types import FunctionType
from typing import Any, Optional, Tuple

from ..types import Config, Context, FieldMeta, FieldType
from .const import ARRAYS
from .context import evaluate
from .fmt import fmt_check
from .misc import pad_up, repstr
from .types import check_types_match, decode_type


def is_sub_class(cls, class_or_tuple) -> bool:
    if not isinstance(class_or_tuple, tuple):
        class_or_tuple = (class_or_tuple,)
    if cls is None:
        return cls in class_or_tuple
    try:
        return issubclass(cls, class_or_tuple)
    except TypeError:
        return False


def field_encode(v: Any) -> Any:
    if isinstance(v, int):
        return v
    if isinstance(v, Enum):
        return v.value
    return v


def field_decode(v: Any, cls: type) -> Any:
    if issubclass(cls, Enum):
        return cls(v)
    return v


def field_get_type(field: Field) -> Tuple[type, Optional[type]]:
    field_type = field.type
    if field_type is Ellipsis:
        return field_type, None
    if field_type is Any:
        return None, None
    if hasattr(field_type, "__origin__"):
        field_type = field.type.__origin__
    if not isinstance(field_type, type):
        return field_type, None
    if issubclass(field_type, ARRAYS) and hasattr(field.type, "__args__"):
        return field_type, field.type.__args__[0]
    return field_type, None


def field_get_meta(field: Field) -> FieldMeta:
    # run some precondition checks for finding common mistakes
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
    # finally fetch the metadata object
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
        if issubclass(meta.types, ds):
            # try to initialize single fields with an empty object
            # noinspection PyArgumentList
            return meta.types()
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
                elif type(meta.base.type) == type:
                    items.append(meta.base.type())
                else:
                    # cannot build non-class types (None, Any, Union, etc.)
                    # bail out, nothing to do
                    return []
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
    # decode field type
    meta.types = decode_type(field.type)

    # Validation checks all standard and wrapper fields, which are based on 4 types:
    # - FIELD - field(), subfield(), built(), adapter()
    # - REPEAT - repeat()
    # - COND - cond()
    # - SWITCH - switch()
    # It also makes sure that special fields (non-public) are used either unwrapped,
    # or with a compatible wrapper field.

    # process special fields (seek, padding, etc)
    # also: wrapper fields that wrap special fields - except switch()
    # (wrapper fields inherit the 'public' property; switch() doesn't)
    if not meta.public:
        if meta.types != type(Ellipsis):
            raise TypeError("Use Ellipsis (...) for special fields")
        # wrapped special fields make the wrappers non-public
        # so accept any special fields that aren't wrappers
        if not meta.base:
            meta.validated = True
            return
        # otherwise only allow wrapping special fields inside cond()
        if meta.ftype != FieldType.COND:
            raise TypeError("Only cond() and switch() can wrap special fields")
    # reject public fields with incorrect type
    # (except switch() fields, as they can wrap special fields)
    elif meta.types == type(Ellipsis) and meta.ftype != FieldType.SWITCH:
        raise TypeError("Cannot use Ellipsis (...) for standard fields")

    is_tuple = isinstance(meta.types, tuple)
    is_valid_repeat = False
    is_valid_union = False
    is_valid_ellipsis = False
    is_valid_simple = False

    # CHECK FIELD VALIDITY DEPENDING ON THE PROPERTY CLASS(ES)

    # generic type (cls, True, args...) - only allow repeat()
    if is_tuple and True in meta.types:
        if meta.types[0] != list:
            # var: dict[int, int] = field(...)
            raise TypeError("Unknown generic type; only list[...] is supported")
        if meta.ftype != FieldType.REPEAT:
            # var: list[int] = field(...)
            raise TypeError("Use repeat() for lists")
        is_valid_repeat = True

    # union type (cls, cls...) - only allow cond() or switch()
    elif is_tuple and len(meta.types):
        if len(meta.types) > 2 and meta.ftype != FieldType.SWITCH:
            # var: int | float | bytes = field(...)
            raise TypeError("Use switch() for union of 3 or more types")
        # len(meta.types) == 2 - cannot be 1
        if meta.ftype not in [FieldType.COND, FieldType.SWITCH]:
            if type(None) in meta.types:
                # var: DataStruct | None = field(...)
                raise TypeError("Use cond() for optional types")
            else:
                # var: DataStruct | OtherStruct = field(...)
                raise TypeError("Use switch()/cond() for union/optional types")
        is_valid_union = True

    # special type Any (empty tuple) - only allow switch()
    elif is_tuple:
        if meta.ftype != FieldType.SWITCH:
            # var: Any = field(...)
            raise TypeError("The 'Any' type can only be used with switch()")

    # special type Ellipsis - only allow cond(), switch()
    elif meta.types == type(Ellipsis):
        if meta.ftype not in [FieldType.COND, FieldType.SWITCH]:
            # var: ... = field(...)
            raise TypeError("The Ellipsis (...) can only be used with switch()/cond()")
        is_valid_ellipsis = True

    # simple types (primitives, DataStruct, etc.)
    else:
        # FieldType.FIELD is used for field(), subfield(), built()
        if isinstance(None, meta.types):
            # var: None = field(...)
            raise TypeError("Cannot use None as field type")
        if is_dataclass(meta.types):
            if meta.fmt is not None and not meta.adapter:
                # var: DataStruct = field(...)
                # var: DataStruct = built(...)
                raise TypeError("Use subfield() for instances of DataStruct")
        else:
            if meta.fmt is None and not meta.base and meta.ftype != FieldType.SWITCH:
                # var: int = subfield()
                raise TypeError("Use field() for non-DataStruct types")
        is_valid_simple = True

    # CHECK FIELD VALIDITY DEPENDING ON THE FIELD TYPE

    if meta.ftype == FieldType.FIELD:
        # validate format specifiers
        if meta.fmt is not None:
            # var: int = field(...)
            fmt_check(meta.fmt)

    elif meta.ftype == FieldType.REPEAT:
        if not is_valid_repeat:
            # var: int = repeat()(...)
            raise TypeError("Can't use repeat() for a non-list field")
        base_field, base_meta = field_get_base(meta)
        if base_meta.builder and not base_meta.always:
            # var: ... = repeat()(built(..., always=False))
            raise TypeError("Built fields inside repeat() are always built")
        if not meta.types[2] and base_meta.ftype == FieldType.FIELD:
            # var: list = repeat()(field(...))
            raise TypeError("Lists of standard fields must be parameterized")
        base_field.name = field.name
        # "unwrap" item types for repeat fields only
        field.type = meta.types[0]
        base_field.type = meta.types[2]
        field_validate(base_field, base_meta)

    elif meta.ftype == FieldType.COND:
        if_not_type = None
        if type(meta.if_not) != FunctionType:
            # cannot get 'if_not=' type for lambdas
            if meta.if_not in [None, Ellipsis]:
                # specified None as default value
                if_not_type = type(None)
            else:
                if_not_type = type(meta.if_not)
        base_field, base_meta = field_get_base(meta)
        base_field.name = field.name
        if is_valid_union:
            # var: int | bool = cond(...)(field(...))
            # var: int | None = cond(...)(field(...))
            # -> len(meta.types) == 2
            # verify that the type is specified for this field
            if if_not_type and if_not_type not in meta.types:
                # var: int | bool = cond(..., if_not=None)(field(...))
                raise TypeError(
                    f"Type of 'if_not=' ({if_not_type}) must be part of the union"
                )
            # for Union[*, None] - use the first non-None type
            if type(None) in meta.types:
                # var: int | None = cond(...)(field(...))
                types = list(meta.types)
                types.remove(type(None))
                base_field.type = types[0]
            # for Union[*, *] - try to guess the two types
            else:
                # var: int | bool = cond(...)(field(...))
                if if_not_type:
                    # var: int | bool = cond(..., if_not=False)(field(...))
                    # 'if_not=' has a known type, simply use the other one
                    types = list(meta.types)
                    types.remove(if_not_type)
                    base_field.type = types[0]
                else:
                    # var: int | bool = cond(..., if_not=lambda ctx: ...)(field(...))
                    # two types - check if any is a DataStruct
                    structs = tuple(is_dataclass(cls) for cls in meta.types)
                    if structs[0] and not structs[1]:
                        # var: DataStruct | int = cond(..., ...)(subfield(...))
                        # var: DataStruct | int = cond(..., ...)(field(...))
                        base_field.type = meta.types[0 if base_meta.fmt is None else 1]
                    elif structs[1] and not structs[0]:
                        # var: int | DataStruct = cond(..., ...)(subfield(...))
                        # var: int | DataStruct = cond(..., ...)(field(...))
                        base_field.type = meta.types[1 if base_meta.fmt is None else 0]
                    else:
                        # var: int | bool = cond(..., ...)(field(...))
                        raise TypeError("Couldn't guess the wrapped field's type")
        elif is_valid_ellipsis:
            # var: ... = cond(...)(field(...))
            # -> meta.types == type(Ellipsis)
            base_field.type = Ellipsis
        elif is_valid_simple:
            # var: int = cond(..., if_not=0)(field(...))
            # -> type(meta.types) == type
            if if_not_type and if_not_type != meta.types:
                # var: int = cond(..., if_not=None)(field(...))
                raise TypeError(
                    f"Type of 'if_not=' ({if_not_type}) different than the field type"
                )
            base_field.type = meta.types
        else:
            raise TypeError("No valid class/type found for cond()")
        field_validate(base_field, base_meta)

    elif meta.ftype == FieldType.SWITCH:
        # if not is_valid_union and not is_valid_any and not is_valid_ellipsis:
        #     # var: int = switch(...)
        #     raise TypeError("Use a union type, 'Any' or '...' for switch() fields")
        # test each case of the switch field
        base_types = []
        for key, (field_type, base_field) in meta.fields.items():
            base_type = decode_type(field_type)
            if not check_types_match(base_type, meta.types):
                # var: int | bool = switch(...)(_1=(bytes, field(...)))
                raise TypeError(
                    f"Case field type {base_type} (for case '{key}') "
                    f"does not fit the switch() field type {meta.types}"
                )
            base_meta = field_get_meta(base_field)
            base_field.name = field.name
            base_field.type = base_type
            field_validate(base_field, base_meta)
            base_types.append(base_type)
        if meta.types == type(Ellipsis) and type(Ellipsis) not in base_types:
            raise TypeError(
                "Cannot use Ellipsis (...) for switch() fields without special fields"
            )

    meta.validated = True
