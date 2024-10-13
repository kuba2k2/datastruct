#  Copyright (c) Kuba Szczodrzyński 2024-10-13.

from dataclasses import dataclass
from typing import Any

import pytest
from base import INPUT, DummyClass

from datastruct import DataStruct
from datastruct.fields import (
    built,
    cond,
    const,
    field,
    padding,
    repeat,
    skip,
    subfield,
    switch,
)


class TestValidationPass:
    def test_simple(self):
        @dataclass
        class TestClass(DataStruct):
            var1: int = field("I")
            var2: bytes = const(b"\x00")(field(1))
            var3: int = built("I", lambda ctx: 0)
            _1: ... = padding(4)
            _2: ... = skip(4)
            var4: int = field("I")
            var5: DummyClass = subfield()

        TestClass.unpack(INPUT)

    def test_repeat(self):
        @dataclass
        class TestClass(DataStruct):
            var1: list[int] = repeat(4)(field("I"))
            var2: list[list[int]] = repeat(4)(repeat(4)(field("I")))
            var3: list = repeat(4)(
                switch(True)(
                    false=(int, field("I")),
                    true=(int, field("H")),
                )
            )
            var4: list[int] = repeat(4)(built("I", lambda ctx: None))

        TestClass.unpack(INPUT)

    def test_combo(self):
        @dataclass
        class TestClass(DataStruct):
            var1: list[int | bool | list[int]] | None = cond(True)(
                repeat(4)(
                    switch(4)(
                        _0=(int, field("I")),
                        _1=(int, field("H")),
                        _2=(bool, field("H")),
                        _3=(bool, field("H")),
                        _4=(list[int], repeat(2)(cond(True, if_not=0)(field("H")))),
                        _5=(list[int | None], repeat(2)(cond(True)(field("H")))),
                    )
                )
            )

        obj = TestClass.unpack(INPUT)
        assert type(obj.var1) == list
        assert type(obj.var1[0]) == list
        assert type(obj.var1[0][0]) == int


class TestValidationFail:
    def test_simple(self):
        @dataclass
        class TestClass1(DataStruct):
            var: None = field("I")

        @dataclass
        class TestClass2(DataStruct):
            var: ... = field("I")

        @dataclass
        class TestClass3(DataStruct):
            var: Any = field("I")

        @dataclass
        class TestClass4(DataStruct):
            var: DummyClass = field("I")

        @dataclass
        class TestClass5(DataStruct):
            var: int = subfield()

        @dataclass
        class TestClass6(DataStruct):
            var: list[int] = field("I")

        @dataclass
        class TestClass7(DataStruct):
            var: int | float | bytes = field("I")

        for cls in (TestClass1, TestClass2):
            with pytest.raises(
                TypeError,
                match="Cannot use .*",
            ):
                cls.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="The 'Any' type can only be used with .*",
        ):
            TestClass3.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Use subfield.* for instances of DataStruct",
        ):
            TestClass4.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Use field.* for non-DataStruct types",
        ):
            TestClass5.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Use repeat.* for lists",
        ):
            TestClass6.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Use switch.* for union of 3 or more types",
        ):
            TestClass7.unpack(INPUT)

    def test_special(self):
        @dataclass
        class TestClass1(DataStruct):
            var: int = padding(4)

        @dataclass
        class TestClass2(DataStruct):
            var: Any = padding(4)

        @dataclass
        class TestClass3(DataStruct):
            var: None = padding(4)

        for cls in (TestClass1, TestClass2, TestClass3):
            with pytest.raises(
                TypeError,
                match="Use Ellipsis .* for special fields",
            ):
                cls.unpack(INPUT)

    def test_repeat(self):
        @dataclass
        class TestClass1(DataStruct):
            var: ... = repeat(4)(repeat(4)(padding(4)))

        @dataclass
        class TestClass2(DataStruct):
            var: int = repeat(4)(field("I"))

        @dataclass
        class TestClass3(DataStruct):
            var: list = repeat(4)(field("I"))

        @dataclass
        class TestClass4(DataStruct):
            var: tuple = repeat(4)(field("I"))

        @dataclass
        class TestClass5(DataStruct):
            var: list[int] = repeat(4)(subfield())

        @dataclass
        class TestClass6(DataStruct):
            var: list[int] = repeat(4)(built("I", lambda ctx: None, always=False))

        with pytest.raises(
            TypeError,
            match="Only cond.* and switch.* can wrap special fields",
        ):
            TestClass1.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Can't use repeat.* for a non-list field",
        ):
            TestClass2.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Lists of standard fields must be parameterized",
        ):
            TestClass3.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Unknown generic type; only list.* is supported",
        ):
            TestClass4.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Use field.* for non-DataStruct types",
        ):
            TestClass5.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Built fields inside repeat.* are always built",
        ):
            TestClass6.unpack(INPUT)
