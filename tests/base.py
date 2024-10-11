#  Copyright (c) Kuba Szczodrzyński 2024-10-11.

import re
from dataclasses import dataclass
from pprint import pformat
from typing import Type

import pytest

from datastruct import DataStruct


@dataclass
class TestData:
    cls: Type[DataStruct] | None = None
    data: bytes | None = None
    obj_full: DataStruct | None = None
    obj_simple: DataStruct | None = None
    full_must_match: bool = False


class TestBase:
    cls: Type[DataStruct]
    test: TestData

    @pytest.fixture(scope="function", autouse=True)
    def setup_and_teardown(self, test: TestData) -> None:
        self.test = test

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
        unpacked = (self.test.cls or self.cls).unpack(self.test.data)
        if self.test.obj_full is None:
            print("Unpacked (from bytes):")
            print(self.obj_to_str(unpacked))
            return
        assert unpacked == self.test.obj_full

    def test_pack_full_to_bytes(self) -> None:
        if self.test.obj_full is None:
            pytest.skip()
        packed = self.test.obj_full.pack()
        if self.test.data is None:
            print("Packed (full):")
            print(self.bytes_to_hex_repr(packed))
            return
        packed = self.bytes_to_hex_str(packed)
        expected = self.bytes_to_hex_str(self.test.data)
        assert packed == expected

    def test_pack_simple_to_bytes(self) -> None:
        if self.test.obj_simple is None:
            pytest.skip()
        packed = self.test.obj_simple.pack()
        if self.test.obj_full is None:
            print("Unpacked (from simple):")
            print(self.obj_to_str(self.test.obj_simple))
        if self.test.data is None:
            print("Packed (simple):")
            print(self.bytes_to_hex_repr(packed))
            return
        packed = self.bytes_to_hex_str(packed)
        expected = self.bytes_to_hex_str(self.test.data)
        assert packed == expected

    def test_obj_full_after_packing(self) -> None:
        if (
            not self.test.full_must_match
            or self.test.obj_full is None
            or self.test.obj_simple is None
        ):
            pytest.skip()
        self.test.obj_simple.pack()
        assert self.test.obj_full == self.test.obj_simple
