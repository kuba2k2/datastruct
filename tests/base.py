#  Copyright (c) Kuba Szczodrzyński 2024-10-11.

import re
from dataclasses import dataclass
from pprint import pformat
from typing import Type

import pytest

from datastruct import DataStruct

INPUT = b"\x00" * 256


@dataclass
class DummyClass(DataStruct):
    pass


@dataclass
class OtherClass(DataStruct):
    pass


@dataclass
class TestData:
    __test__ = False

    cls: Type[DataStruct] | None = None
    data: bytes | None = None
    obj_full: DataStruct | None = None
    obj_simple: DataStruct | None = None
    context: dict = None

    full_after_packing: bool = True
    unpack_then_pack: bool = True
    pack_then_unpack: bool = True

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}


class TestBase:
    test: TestData

    @pytest.fixture(scope="function", autouse=True)
    def setup_and_teardown(self, test: TestData) -> None:
        self.test = test

    def get_cls(self) -> Type[DataStruct]:
        return self.test.cls or type(self.test.obj_full) or type(self.test.obj_simple)

    def obj_to_str(self, obj: DataStruct) -> str:
        pp = pformat(obj)
        # fix enum representation
        pp = re.sub(r"<([^.]+\.[^:]+?):.+?>", "\\1", pp)
        pp = re.sub(r"([A-Za-z][A-Za-z0-9]+?)\.0", "\\1(0)", pp)
        return pp

    def bytes_to_hex_repr(self, data: bytes) -> str:
        out = ""
        for i in range(0, len(data), 16):
            line = data[i : i + 16]
            out += 'b"\\x' + line.hex(" ").replace(" ", "\\x") + '"\n'
        return out

    def bytes_to_hex_str(self, data: bytes) -> str:
        out = ""
        for i in range(0, len(data), 16):
            line = data[i : i + 16]
            out += line.hex(" ") + "\n"
        return out

    def test_unpack_from_bytes(self) -> None:
        if self.test.data is None:
            pytest.skip()
        unpacked = self.get_cls().unpack(self.test.data, **self.test.context)
        if self.test.obj_full is None:
            print("Unpacked (from bytes):")
            print(self.obj_to_str(unpacked))
            return
        if unpacked != self.test.obj_full:
            print()
            print(unpacked)
            print(self.test.obj_full)
        assert unpacked == self.test.obj_full

    def test_pack_full_to_bytes(self) -> None:
        if self.test.obj_full is None:
            pytest.skip()
        packed = self.test.obj_full.pack(**self.test.context)
        if self.test.data is None:
            print("Packed (full):")
            print(self.bytes_to_hex_repr(packed))
            return
        if packed != self.test.data:
            print()
            print(packed.hex(" "))
            print(self.test.data.hex(" "))
        assert packed == self.test.data

    def test_pack_simple_to_bytes(self) -> None:
        if self.test.obj_simple is None:
            pytest.skip()
        packed = self.test.obj_simple.pack(**self.test.context)
        if self.test.obj_full is None:
            print("Unpacked (from simple):")
            print(self.obj_to_str(self.test.obj_simple))
        if self.test.data is None:
            print("Packed (simple):")
            print(self.bytes_to_hex_repr(packed))
            return
        if packed != self.test.data:
            print()
            print(packed.hex(" "))
            print(self.test.data.hex(" "))
        assert packed == self.test.data

    def test_full_after_packing(self) -> None:
        if (
            not self.test.full_after_packing
            or self.test.obj_full is None
            or self.test.obj_simple is None
        ):
            pytest.skip()
        self.test.obj_simple.pack(**self.test.context)
        if self.test.obj_full != self.test.obj_simple:
            print()
            print(self.test.obj_full)
            print(self.test.obj_simple)
        assert self.test.obj_full == self.test.obj_simple

    def test_unpack_then_pack(self) -> None:
        if not self.test.unpack_then_pack or self.test.data is None:
            pytest.skip()
        unpacked = self.get_cls().unpack(self.test.data, **self.test.context)
        packed = unpacked.pack(**self.test.context)
        if packed != self.test.data:
            print()
            print(packed.hex(" "))
            print(self.test.data.hex(" "))
        assert packed == self.test.data

    def test_pack_then_unpack(self) -> None:
        if not self.test.pack_then_unpack or self.test.obj_full is None:
            pytest.skip()
        packed = self.test.obj_full.pack(**self.test.context)
        unpacked = self.get_cls().unpack(packed, **self.test.context)
        if unpacked != self.test.obj_full:
            print()
            print(unpacked)
            print(self.test.obj_full)
        assert unpacked == self.test.obj_full
