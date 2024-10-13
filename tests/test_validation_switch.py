#  Copyright (c) Kuba Szczodrzyński 2024-10-13.

from dataclasses import dataclass
from typing import Any

import pytest
from base import INPUT, DummyClass, OtherClass

from datastruct import DataStruct
from datastruct.fields import cond, field, padding, repeat, subfield, switch


@dataclass
class WithBase1(DummyClass):
    pass


@dataclass
class WithBase2(DummyClass):
    pass


class TestValidationSwitchPass:
    def test_switch_simple(self):
        @dataclass
        class TestClass(DataStruct):
            var1: int = switch(False)(
                false=(int, field("H")),
                true=(int, field("I")),
            )
            var2: DummyClass | OtherClass = switch(False)(
                false=(DummyClass, subfield()),
                true=(OtherClass, subfield()),
            )
            var3: DummyClass = switch(False)(
                false=(WithBase1, subfield()),
                true=(WithBase2, subfield()),
            )
            var4: DummyClass | int = switch(False)(
                false=(WithBase1, subfield()),
                true=(WithBase2, subfield()),
                _1=(int, field("I")),
            )
            var5: DummyClass | None = switch(False)(
                false=(WithBase1, subfield()),
                true=(WithBase2, subfield()),
                _1=(DummyClass | None, cond(False)(subfield())),
            )
            var6: int | bool | list[int] = switch(4)(
                _0=(int, field("I")),
                _1=(int, field("H")),
                _2=(bool, field("H")),
                _3=(bool, field("H")),
                _4=(list[int], repeat(2)(field("H"))),
            )

        TestClass.unpack(INPUT)

    def test_switch_any(self):
        @dataclass
        class TestClass(DataStruct):
            var1: Any = switch(False)(
                false=(int, field("H")),
                true=(int, field("I")),
            )
            var2: Any = switch(False)(
                false=(DummyClass, subfield()),
                true=(OtherClass, subfield()),
            )
            var3: Any = switch(False)(
                false=(..., padding(4)),
                true=(int, field("I")),
            )

        TestClass.unpack(INPUT)

    def test_switch_ellipsis(self):
        @dataclass
        class TestClass(DataStruct):
            var1: ... = cond(True)(
                switch(False)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                    _1=(..., padding(4)),
                )
            )
            var2: ... = switch(False)(
                false=(..., padding(4)),
                true=(int, field("I")),
            )
            var3: int | None = switch(False)(
                false=(..., padding(4)),
                true=(int, field("I")),
            )

        TestClass.unpack(INPUT)


class TestValidationSwitchFail:
    def test_switch_type_not_matched(self):
        @dataclass
        class TestClass1(DataStruct):
            var: int = switch(False)(
                false=(int, field("H")),
                true=(bytes, field("I")),
            )

        @dataclass
        class TestClass2(DataStruct):
            var: list[bytes | bool] = repeat(4)(
                switch(True)(
                    false=(int, field("I")),
                    true=(int, field("H")),
                )
            )

        @dataclass
        class TestClass3(DataStruct):
            var: DummyClass = switch(False)(
                false=(DummyClass, subfield()),
                true=(OtherClass, subfield()),
            )

        @dataclass
        class TestClass4(DataStruct):
            var: int | bool = switch(4)(
                _0=(int, field("I")),
                _2=(bool, field("H")),
                _4=(list[int], repeat(2)(field("H"))),
            )

        for cls in (TestClass1, TestClass2, TestClass3, TestClass4):
            with pytest.raises(
                TypeError,
                match="Case field type .* does not fit the switch.* field type",
            ):
                cls.unpack(INPUT)

    def test_switch_ellipsis(self):
        @dataclass
        class TestClass1(DataStruct):
            var: ... = cond(True)(
                switch(False)(
                    false=(DummyClass, subfield()),
                    true=(OtherClass, subfield()),
                )
            )

        with pytest.raises(
            TypeError,
            match="Cannot use Ellipsis .* for switch.* fields without special fields",
        ):
            TestClass1.unpack(INPUT)
