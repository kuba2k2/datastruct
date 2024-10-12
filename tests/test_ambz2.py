#  Copyright (c) Kuba Szczodrzyński 2024-10-11.

import pytest
from base import TestBase, TestData
from test_ambz2_structs import *
from util import read_data_file

config = get_image_config()


def build_firmware():
    # defaults from libretiny/boards/bw15
    board_flash = {
        "part_table": (0x000000, 0x1000, 0x000000 + 0x1000),
        "system": (0x001000, 0x1000, 0x001000 + 0x1000),
        "calibration": (0x002000, 0x1000, 0x002000 + 0x1000),
        "boot": (0x004000, 0x8000, 0x004000 + 0x8000),
        "ota1": (0x00C000, 0xF8000, 0x00C000 + 0xF8000),
        "ota2": (0x104000, 0xF8000, 0x104000 + 0xF8000),
        "kvs": (0x1FC000, 0x4000, 0x1FC000 + 0x400),
    }

    ptab_offset, _, ptab_end = board_flash["part_table"]
    boot_offset, _, boot_end = board_flash["boot"]
    ota1_offset, _, ota1_end = board_flash["ota1"]

    # build the partition table
    ptable = PartitionTable(user_data=b"\xFF" * 256)
    for region, type in config.ptable.items():
        offset, length, _ = board_flash[region]
        hash_key = config.keys.hash_keys[region]
        ptable.partitions.append(
            PartitionRecord(offset, length, type, hash_key=hash_key),
        )
    ptable = Image(
        keyblock=build_keyblock(config, "part_table"),
        header=ImageHeader(
            type=ImageType.PARTAB,
        ),
        data=ptable,
    )

    # build boot image
    region = "boot"
    boot = Image(
        keyblock=build_keyblock(config, region),
        header=ImageHeader(
            type=ImageType.BOOT,
            user_keys=[config.keys.user_keys[region], FF_32],
        ),
        data=build_section(config.boot),
    )

    # build firmware (sub)images
    firmware = []
    region = "ota1"
    for idx, image in enumerate(config.fw):
        obj = Image(
            keyblock=build_keyblock(config, region),
            header=ImageHeader(
                type=image.type,
                # use FF to allow recalculating by OTA code
                serial=0xFFFFFFFF if idx == 0 else 0,
                user_keys=(
                    [FF_32, config.keys.user_keys[region]]
                    if idx == 0
                    else [FF_32, FF_32]
                ),
            ),
            data=Firmware(
                sections=[build_section(section) for section in image.sections],
            ),
        )
        # remove empty sections
        obj.data.sections = [s for s in obj.data.sections if s.data]
        firmware.append(obj)
        if image.type != ImageType.XIP:
            continue
        # update SCE keys for XIP images
        for section in obj.data.sections:
            section.header.sce_key = config.keys.xip_sce_key
            section.header.sce_iv = config.keys.xip_sce_iv

    # build main flash image
    return Flash(
        ptable=ptable,
        boot=boot,
        firmware=firmware,
    )


TEST_DATA = [
    pytest.param(
        TestData(
            cls=Flash,
            data=read_data_file(TEST_DATA_URLS["image_flash_is.bin"]),
            obj_full=None,
            obj_simple=build_firmware(),
            context=dict(
                hash_key=config.keys.hash_keys["part_table"],
            ),
        ),
        id="dummy",
    ),
]


@pytest.mark.parametrize("test", TEST_DATA)
class TestAmbZ2(TestBase):
    pass


del TestBase
