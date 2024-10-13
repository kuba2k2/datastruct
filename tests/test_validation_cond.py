#  Copyright (c) Kuba Szczodrzyński 2024-10-13.

from dataclasses import dataclass
from typing import Any, Union

import pytest
from base import INPUT, DummyClass, OtherClass

from datastruct import DataStruct
from datastruct.fields import cond, field, padding, subfield, switch


class TestValidationCondPass:
    def test_cond_if_not_type(self):
        @dataclass
        class TestClass(DataStruct):
            var1: int = cond(True, if_not=0)(field("I"))
            var2: Union[int] = cond(True, if_not=0)(field("I"))
            var3: int = cond(True, if_not=lambda ctx: None)(field("I"))
            var4: DummyClass = cond(True, if_not=DummyClass())(subfield())

        TestClass.unpack(INPUT)

    def test_cond_if_not_type_union(self):
        @dataclass
        class TestClass(DataStruct):
            var1: int | None = cond(True)(field("I"))
            var2: int | bool = cond(True, if_not=False)(field("I"))
            var3: int | DummyClass = cond(True, if_not=DummyClass())(field("I"))
            var4: int | DummyClass = cond(True, if_not=0)(subfield())
            var5: int | None = cond(True, if_not=lambda ctx: None)(field("I"))
            var6: DummyClass | None = cond(True)(subfield())

        TestClass.unpack(INPUT)

    def test_cond_type_guess(self):
        @dataclass
        class TestClass(DataStruct):
            var1: int | DummyClass = cond(True, if_not=lambda ctx: None)(field("I"))
            var2: int | DummyClass = cond(True, if_not=lambda ctx: None)(subfield())
            var3: DummyClass | OtherClass = cond(True, if_not=OtherClass())(subfield())

        TestClass.unpack(INPUT)

    def test_cond_special(self):
        @dataclass
        class TestClass(DataStruct):
            var1: ... = cond(True)(padding(4))

        TestClass.unpack(INPUT)

    def test_cond_switch(self):
        @dataclass
        class TestClass(DataStruct):
            var1: Any = cond(True)(
                switch(True)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                )
            )
            var2: DummyClass | OtherClass | None = cond(True)(
                switch(True)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                )
            )
            var3: DummyClass | OtherClass = cond(True, if_not=DummyClass())(
                switch(True)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                )
            )
            var4: ... = cond(True)(
                switch(True)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                    _1=(..., padding(4)),
                )
            )

        TestClass.unpack(INPUT)


class TestValidationCondFail:
    def test_cond_if_not_type(self):
        @dataclass
        class TestClass1(DataStruct):
            var: int = cond(True)(field("I"))

        @dataclass
        class TestClass2(DataStruct):
            var: int = cond(True, if_not=None)(field("I"))

        @dataclass
        class TestClass3(DataStruct):
            var: int = cond(True, if_not=False)(field("I"))

        @dataclass
        class TestClass4(DataStruct):
            var: DummyClass = cond(True)(subfield())

        for cls in (TestClass1, TestClass2, TestClass3, TestClass4):
            with pytest.raises(
                TypeError,
                match="Type of 'if_not=' .* different than the field type",
            ):
                cls.unpack(INPUT)

    def test_cond_if_not_type_union(self):
        @dataclass
        class TestClass1(DataStruct):
            var: int | bool = cond(True)(field("I"))

        @dataclass
        class TestClass2(DataStruct):
            var: int | bool = cond(True, if_not=None)(field("I"))

        @dataclass
        class TestClass3(DataStruct):
            var: int | None = cond(True, if_not=False)(field("I"))

        @dataclass
        class TestClass4(DataStruct):
            var: DummyClass | OtherClass = cond(True)(
                switch(True)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                )
            )

        for cls in (TestClass1, TestClass2, TestClass3, TestClass4):
            with pytest.raises(
                TypeError,
                match="Type of 'if_not=' .* must be part of the union",
            ):
                cls.unpack(INPUT)

    def test_cond_type_guess(self):
        @dataclass
        class TestClass1(DataStruct):
            var: int | bool = cond(True, if_not=lambda ctx: None)(field("I"))

        @dataclass
        class TestClass2(DataStruct):
            var: DummyClass | OtherClass = cond(
                True,
                if_not=lambda ctx: None,
            )(subfield())

        for cls in (TestClass1, TestClass2):
            with pytest.raises(
                TypeError,
                match="Couldn't guess the wrapped field's type",
            ):
                cls.unpack(INPUT)

    def test_cond_type_guess_if_not(self):
        @dataclass
        class TestClass1(DataStruct):
            var: int | DummyClass = cond(True, if_not=DummyClass())(subfield())

        @dataclass
        class TestClass2(DataStruct):
            var: int | DummyClass = cond(True, if_not=0)(field("I"))

        @dataclass
        class TestClass3(DataStruct):
            var: DummyClass | None = cond(True)(field("I"))

        with pytest.raises(
            TypeError,
            match="Use field.* for non-DataStruct types",
        ):
            TestClass1.unpack(INPUT)

        for cls in (TestClass2, TestClass3):
            with pytest.raises(
                TypeError,
                match="Use subfield.* for instances of DataStruct",
            ):
                cls.unpack(INPUT)

    def test_cond_wrong_type(self):
        @dataclass
        class TestClass1(DataStruct):
            var: Any = cond(True)(padding(4))

        @dataclass
        class TestClass2(DataStruct):
            var: None = cond(True)(padding(4))

        @dataclass
        class TestClass3(DataStruct):
            var: Any = cond(True)(field("I"))

        @dataclass
        class TestClass4(DataStruct):
            var: ... = cond(True)(field("I"))

        @dataclass
        class TestClass5(DataStruct):
            var: None = cond(True)(field("I"))

        for cls in (TestClass1, TestClass2):
            with pytest.raises(
                TypeError,
                match="Use Ellipsis .* for special fields",
            ):
                cls.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="The 'Any' type can only be used with .*",
        ):
            TestClass3.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Cannot use Ellipsis .* for standard fields",
        ):
            TestClass4.unpack(INPUT)

        with pytest.raises(
            TypeError,
            match="Cannot use None as field type",
        ):
            TestClass5.unpack(INPUT)
