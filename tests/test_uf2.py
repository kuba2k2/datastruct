#  Copyright (c) Kuba Szczodrzyński 2024-10-11.

import pytest
from base import TestBase, TestData
from test_uf2_structs import *

TEST_DATA = [
    pytest.param(
        TestData(
            data=(
                b"\x30\x31\x50\x45\x61\x70\x70\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x66\x6c\x61\x73\x68\x30\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x10\x01\x00\x00\x10\x12\x00\x00\x00\x00\x00"
                b"\x30\x31\x50\x45\x64\x6f\x77\x6e\x6c\x6f\x61\x64\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x66\x6c\x61\x73\x68\x30\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x20\x13\x00\x00\x60\x0a\x00\x00\x00\x00\x00"
            ),
            obj_full=PartitionTable(
                partitions=[
                    Partition(
                        magic_word=1162883376,
                        name="app",
                        flash_name="flash0",
                        offset=69632,
                        length=1183744,
                    ),
                    Partition(
                        magic_word=1162883376,
                        name="download",
                        flash_name="flash0",
                        offset=1253376,
                        length=679936,
                    ),
                ]
            ),
            obj_simple=PartitionTable(
                partitions=[
                    Partition(
                        name="app",
                        flash_name="flash0",
                        offset=69632,
                        length=1183744,
                    ),
                    Partition(
                        name="download",
                        flash_name="flash0",
                        offset=1253376,
                        length=679936,
                    ),
                ]
            ),
            context=dict(
                name_len=16,
                length=0x30 * 2,
            ),
        ),
        id="uf2_partition_table",
    ),
    pytest.param(
        TestData(
            data=(
                b"\x30\x31\x50\x45\x61\x70\x70\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x66\x6c\x61\x73"
                b"\x68\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x10\x01\x00\x00\x10\x12\x00\x00\x00\x00\x00"
            ),
            obj_full=Partition(
                magic_word=1162883376,
                name="app",
                flash_name="flash0",
                offset=69632,
                length=1183744,
            ),
            obj_simple=Partition(
                name="app",
                flash_name="flash0",
                offset=69632,
                length=1183744,
            ),
        ),
        id="uf2_partition",
    ),
]


@pytest.mark.parametrize("test", TEST_DATA)
class TestUF2(TestBase):
    pass


del TestBase
