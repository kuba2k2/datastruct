#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

import dataclasses
import struct
from dataclasses import MISSING, Field, dataclass
from typing import IO, Any, Dict, Generator, List, Optional, Tuple, Type, TypeVar, Union

from .types import Context, Endianness, FieldMeta, FieldType, T
from .utils.const import ARRAYS, EXCEPTIONS
from .utils.context import build_context, evaluate
from .utils.fields import (
    field_decode,
    field_do_seek,
    field_encode,
    field_get_base,
    field_get_meta,
    field_validate,
)
from .utils.fmt import fmt_evaluate
from .utils.public import get_default_endianness


@dataclass
class DataStruct:
    def __post_init__(self) -> None:
        for field, meta, value in self.fields():
            field_validate(field, meta)

            # accept fields already having a value
            if value != Ellipsis:
                continue

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
                    # noinspection PyArgumentList
                    self.__setattr__(field.name, field.type(items))
                else:
                    # build an empty list for variable-length subfields
                    # (when 'count' can't be determined at init-time)
                    self.__setattr__(field.name, [])
                continue

            if meta.ftype == FieldType.FIELD and not meta.builder:
                if issubclass(field.type, DataStruct):
                    # try to initialize single fields with an empty object
                    self.__setattr__(field.name, field.type())
                    continue
                # forbid creating an instance of fields with no default
                raise ValueError(
                    f"Cannot create an instance of {type(self)}: "
                    f"field '{field.name}' has no default and "
                    f"no value was passed",
                )

    def _write(self, ctx: Context, meta: FieldMeta, value: Any) -> Any:
        # build fields if necessary
        if meta.builder and (value is Ellipsis or meta.always):
            value = evaluate(ctx, meta.builder)
        # pack structures directly
        if isinstance(value, DataStruct):
            value.pack(io=ctx.io, parent=ctx)
            return value
        # use struct.pack() to write the raw value
        fmt = fmt_evaluate(ctx, meta.fmt, self.endianness())
        encoded = field_encode(value)
        ctx.io.write(struct.pack(fmt, encoded))
        return value

    def _pack(
        self,
        io: IO[bytes],
        parent: Optional["Context"] = None,
    ) -> Generator[str, None, None]:
        fields = self.fields()
        values = {f.name: v for f, m, v in fields if v != Ellipsis}
        ctx = build_context(parent, io, packing=True, unpacking=False, **values)

        for field, meta, value in fields:
            yield field.name
            # print(f"Packing field '{type(self).__name__}.{field.name}'")

            if meta.ftype == FieldType.SEEK:
                field_do_seek(ctx, meta)
                continue
            if meta.ftype == FieldType.PADDING:
                length = evaluate(ctx, meta.length)
                padding = meta.pattern * length
                io.write(padding)
                continue

            if meta.ftype != FieldType.REPEAT:
                value = self._write(ctx, meta, value)
                # update built value in the actual object
                setattr(self, field.name, value)
                setattr(ctx, field.name, value)
                continue

            # repeat() field - value type must be List
            if not isinstance(value, ARRAYS):
                raise TypeError("Value is not an array")
            items: Union[list, tuple] = value

            i = 0
            count = evaluate(ctx, meta.count)
            base_field, base_meta = field_get_base(meta)
            items_iter = iter(items)

            if isinstance(count, int) and len(value) != count and not base_meta.builder:
                # ensure the list size matches expected element count,
                # apart from built() subfields, which are implicitly trusted here
                raise ValueError(
                    f"List size ({len(value)}) doesn't match "
                    f"repeat() 'count' parameter value ({count})",
                )

            while count is None or i < count:
                yield f"{field.name}[{i}]"
                ctx.i = i
                if meta.when and not evaluate(ctx, meta.when):
                    break

                if not base_meta.builder:
                    item = next(items_iter)
                else:
                    item = Ellipsis
                item = self._write(ctx, base_meta, item)
                if isinstance(items, list):
                    # don't reassign built fields to tuples
                    # only update in lists (which will update the object too)
                    if len(items) <= i:
                        items.append(item)
                    else:
                        items[i] = item

                # provide another value 'item' to context lambdas in 'last'
                ctx.item = item
                last = evaluate(ctx, meta.last)
                ctx.pop("item")
                if last:
                    break
                i += 1
            ctx.pop("i", None)
        yield None

    @classmethod
    def _read(cls, ctx: Context, meta: FieldMeta, typ: Type[T]) -> T:
        # unpack structures directly
        if issubclass(typ, DataStruct):
            return typ.unpack(io=ctx.io, parent=ctx)
        # use struct.unpack() to read the raw value
        fmt = fmt_evaluate(ctx, meta.fmt, cls.endianness())
        length = struct.calcsize(fmt)
        (value,) = struct.unpack(fmt, ctx.io.read(length))
        value = field_decode(value, type)
        return value

    @classmethod
    def _unpack(
        cls: Type["DS"],
        io: IO[bytes],
        parent: Optional[Context] = None,
    ) -> Generator[str, None, "DS"]:
        fields = cls.classfields()
        values = {}
        ctx = build_context(parent, io, packing=False, unpacking=True)

        for field, meta in fields:
            yield field.name
            # validate fields since they weren't validated before
            field_validate(field, meta)
            # print(f"Unpacking field '{cls.__name__}.{field.name}'")

            if meta.ftype == FieldType.SEEK:
                field_do_seek(ctx, meta)
                continue
            if meta.ftype == FieldType.PADDING:
                length = evaluate(ctx, meta.length)
                padding = meta.pattern * length
                if io.read(length) != padding:
                    raise ValueError(f"Invalid padding found")
                continue

            if meta.ftype != FieldType.REPEAT:
                value = cls._read(ctx, meta, field.type)
                ctx[field.name] = value
                values[field.name] = value
                continue

            # repeat() field - value type must be List
            if not issubclass(field.type, ARRAYS):
                raise TypeError("Field type is not an array")

            i = 0
            count = evaluate(ctx, meta.count)
            base_field, base_meta = field_get_base(meta)
            items = []

            while count is None or i < count:
                yield f"{field.name}[{i}]"
                ctx.i = i
                if meta.when and not evaluate(ctx, meta.when):
                    break

                item = cls._read(ctx, base_meta, base_field.type)
                items.append(item)
                values[field.name] = items
                ctx[field.name] = items

                # provide another value 'item' to context lambdas in 'last'
                ctx.item = item
                last = evaluate(ctx, meta.last)
                ctx.pop("item")
                if last:
                    break
                i += 1
            ctx.pop("i", None)
        yield "<constructor>"
        # noinspection PyArgumentList
        return cls(**values)

    def pack(
        self,
        io: IO[bytes],
        parent: Optional["Context"] = None,
    ) -> None:
        cls = type(self)
        suffix = ""
        try:
            for name in self._pack(io, parent):
                suffix = f"{cls.__name__}.{name}" if name else cls.__name__
        except EXCEPTIONS as e:
            suffix = f"; while packing '{suffix}'" if suffix else ""
            e.args = (e.args[0] + suffix,)
            raise e

    @classmethod
    def unpack(
        cls: Type["DS"],
        io: IO[bytes],
        parent: Optional[Context] = None,
    ) -> "DS":
        suffix = ""
        try:
            gen = cls._unpack(io, parent)
            while True:
                name = next(gen)
                suffix = f"{cls.__name__}.{name}" if name else cls.__name__
        except StopIteration as e:
            return e.value
        except EXCEPTIONS as e:
            suffix = f"; while unpacking '{suffix}'" if suffix else ""
            e.args = (e.args[0] + suffix,)
            raise e

    def fields(self) -> List[Tuple[Field, FieldMeta, Any]]:
        return [
            (
                field,
                field_get_meta(field),
                self.__getattribute__(field.name),
            )
            for field in dataclasses.fields(self)
        ]

    @classmethod
    def classfields(cls) -> List[Tuple[Field, FieldMeta]]:
        return [
            (
                field,
                field_get_meta(field),
            )
            for field in dataclasses.fields(cls)
        ]

    def asdict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def endianness(cls) -> Endianness:
        endianness = getattr(cls, "_ENDIANNESS", None)
        if endianness is None:
            return get_default_endianness()
        return endianness


DS = TypeVar("DS", bound=DataStruct)
