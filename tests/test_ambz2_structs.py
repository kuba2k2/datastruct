#  Copyright (c) Kuba Szczodrzyński 2023-1-19.
#  https://github.com/libretiny-eu/ltchiptool/tree/master/ltchiptool/soc/ambz2/util/models

from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from hashlib import sha256
from hmac import HMAC
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, TypeVar

from util import read_data_file

from datastruct import Adapter, Context, DataStruct, datastruct, sizeof
from datastruct.fields import (
    action,
    adapter,
    align,
    alignto,
    bitfield,
    built,
    checksum_end,
    checksum_field,
    checksum_start,
    cond,
    field,
    packing,
    padding,
    repeat,
    subfield,
    switch,
)
from datastruct.utils.misc import pad_up

GITHUB_URL = "https://github.com/kuba2k2/datastruct/raw/refs/heads/test-data/tests"
TEST_DATA_URLS = {
    "image_flash_is.bin": f"{GITHUB_URL}/test_ambz2.image_flash_is.bin",
    "raw.boot.sram.bin": f"{GITHUB_URL}/test_ambz2.raw.boot.sram.bin",
    "raw.fwhs.sram.bin": f"{GITHUB_URL}/test_ambz2.raw.fwhs.sram.bin",
    "raw.fwhs.xip_c.bin": f"{GITHUB_URL}/test_ambz2.raw.fwhs.xip_c.bin",
    "raw.fwhs.xip_p.bin": f"{GITHUB_URL}/test_ambz2.raw.fwhs.xip_p.bin",
}

FLASH_CALIBRATION = b"\x99\x99\x96\x96\x3F\xCC\x66\xFC\xC0\x33\xCC\x03\xE5\xDC\x31\x62"

FF_48 = b"\xFF" * 48
FF_32 = b"\xFF" * 32
FF_16 = b"\xFF" * 16

T = TypeVar("T")


def str2enum(cls: Type[Enum], key: str):
    if not key:
        return None
    try:
        return next(e for e in cls if e.name.lower() == key.lower())
    except StopIteration:
        return None


class FlashSpeed(IntEnum):
    F_100MHZ = 0xFFFF
    F_83MHZ = 0x7FFF
    F_71MHZ = 0x3FFF
    F_62MHZ = 0x1FFF
    F_55MHZ = 0x0FFF
    F_50MHZ = 0x07FF
    F_45MHZ = 0x03FF


class FlashMode(IntEnum):
    QIO = 0xFFFF  # Quad IO
    QO = 0x7FFF  # Quad Output
    DIO = 0x3FFF  # Dual IO
    DO = 0x1FFF  # Dual Output
    SINGLE = 0x0FFF  # One IO


@dataclass
class SystemData(DataStruct):
    @dataclass
    class ForceOldOTA:
        is_disabled: bool
        port: int
        pin: int

    @dataclass
    class RSIPMask:
        length: int
        offset: int
        is_disabled: bool

    # OTA section
    ota2_address: int = field("I", default=0xFFFFFFFF)
    ota2_switch: int = field("I", default=0xFFFFFFFF)
    force_old_ota: ForceOldOTA = bitfield("b1P1u1u5", ForceOldOTA, 0xFF)
    # RDP section (AmebaZ only)
    _1: ... = alignto(0x10)
    rdp_address: int = field("I", default=0xFFFFFFFF)
    rdp_length: int = field("I", default=0xFFFFFFFF)
    # Flash section
    _2: ... = alignto(0x20)
    flash_mode: FlashMode = field("H", default=FlashMode.QIO)
    flash_speed: FlashSpeed = field("H", default=FlashSpeed.F_100MHZ)  # AmebaZ only
    flash_id: int = field("H", default=0xFFFF)
    flash_size_mb: int = adapter(
        encode=lambda v, ctx: 0xFFFF if v == 2 else (v << 10) - 1,
        decode=lambda v, ctx: 2 if v == 0xFFFF else (v + 1) >> 10,
    )(field("H", default=2))
    flash_status: int = field("H", default=0x0000)
    # Log UART section
    _3: ... = alignto(0x30)
    baudrate: int = adapter(
        encode=lambda v, ctx: 0xFFFFFFFF if v == 115200 else v,
        decode=lambda v, ctx: 115200 if v == 0xFFFFFFFF else v,
    )(field("I", default=115200))
    # Calibration data (AmebaZ2 only)
    _4: ... = alignto(0x40)
    spic_calibration: bytes = field("16s", default=FF_16)
    # RSIP section (AmebaZ only)
    _5: ... = alignto(0x50)
    rsip_mask1: RSIPMask = bitfield("u7P2u22u1", RSIPMask, 0xFFFFFFFF)
    rsip_mask2: RSIPMask = bitfield("u7P2u22u1", RSIPMask, 0xFFFFFFFF)
    # Calibration data (AmebaZ2 only)
    _6: ... = alignto(0xFE0)
    bt_ftl_gc_status: int = field("I", default=0xFFFFFFFF)
    _7: ... = alignto(0xFF0)
    bt_calibration: bytes = field("16s", default=FF_16)


class ImageType(IntEnum):
    PARTAB = 0
    BOOT = 1
    FWHS_S = 2
    FWHS_NS = 3
    FWLS = 4
    ISP = 5
    VOE = 6
    WLN = 7
    XIP = 8
    CPFW = 9
    WOWLN = 10
    CINIT = 11


class PartitionType(IntEnum):
    PARTAB = 0
    BOOT = 1
    SYS = 2
    CAL = 3
    USER = 4
    FW1 = 5
    FW2 = 6
    VAR = 7
    MP = 8
    RDP = 9


class SectionType(IntEnum):
    DTCM = 0x80
    ITCM = 0x81
    SRAM = 0x82
    PSRAM = 0x83
    LPDDR = 0x84
    XIP = 0x85


class EncAlgo(IntEnum):
    AES_EBC = 0
    AES_CBC = 1
    OTHER = 0xFF


class HashAlgo(IntEnum):
    MD5 = 0
    SHA256 = 1
    OTHER = 0xFF


def index(func: Callable[[T], int], iterable: Iterable[T], default: T = None) -> T:
    for idx, item in enumerate(iterable):
        if func(item):
            return idx
    return default


class BitFlag(Adapter):
    def encode(self, value: bool, ctx: Context) -> int:
        return 0xFF if value else 0xFE

    def decode(self, value: int, ctx: Context) -> bool:
        return value & 1 == 1


def header_is_last(ctx: Context) -> bool:
    header: SectionHeader = ctx.P.item.header
    return header.next_offset == 0xFFFFFFFF


@dataclass
class Keyblock(DataStruct):
    decryption: bytes = field("32s", default=FF_32)
    hash: bytes = field("32s", default=FF_32)


@dataclass
class KeyblockOTA(DataStruct):
    decryption: bytes = field("32s", default=FF_32)
    reserved: List[bytes] = repeat(5)(field("32s", default=FF_32))


@dataclass
class ImageHeader(DataStruct):
    class Flags(IntFlag):
        HAS_KEY1 = 1 << 0
        HAS_KEY2 = 1 << 1

    length: int = built("I", lambda ctx: sizeof(ctx._.data))
    next_offset: int = field("I", default=0xFFFFFFFF)
    type: ImageType = field("B")
    is_encrypted: bool = field("?", default=False)
    idx_pkey: int = field("B", default=0xFF)
    flags: Flags = built(
        "B",
        lambda ctx: ImageHeader.Flags(
            int(ctx.user_keys[0] != FF_32) + 2 * int(ctx.user_keys[1] != FF_32)
        ),
    )
    _1: ... = padding(8)
    serial: int = field("I", default=0)
    _2: ... = padding(8)
    user_keys: List[bytes] = repeat(2)(field("32s", default=FF_32))


@dataclass
class SectionHeader(DataStruct):
    length: int = built("I", lambda ctx: sizeof(ctx._.entry) + sizeof(ctx._.data))
    next_offset: int = field("I", default=0xFFFFFFFF)
    type: SectionType = field("B")
    sce_enabled: bool = field("?", default=False)
    xip_page_size: int = field("B", default=0)
    xip_block_size: int = field("B", default=0)
    _1: ... = padding(4)
    valid_pattern: bytes = field("8s", default=bytes(range(8)))
    sce_key_iv_valid: bool = adapter(BitFlag())(
        built("B", lambda ctx: ctx.sce_key != FF_16 and ctx.sce_iv != FF_16),
    )
    _2: ... = padding(7)
    sce_key: bytes = field("16s", default=FF_16)
    sce_iv: bytes = field("16s", default=FF_16)
    _3: ... = padding(32)


@dataclass
@datastruct(repeat_fill=True)
class EntryHeader(DataStruct):
    length: int = built("I", lambda ctx: sizeof(ctx._.data))
    address: int = field("I")
    entry_table: List[int] = repeat(6)(field("I", default=0xFFFFFFFF))


@dataclass
class FST(DataStruct):
    class Flags(IntFlag):
        ENC_EN = 1 << 0
        HASH_EN = 2 << 0

    enc_algo: EncAlgo = field("H", default=EncAlgo.AES_CBC)
    hash_algo: HashAlgo = field("H", default=HashAlgo.SHA256)
    part_size: int = field("I", default=0)
    valid_pattern: bytes = field("8s", default=bytes(range(8)))
    _1: ... = padding(4)
    flags: Flags = field("B", default=Flags.HASH_EN)
    cipher_key_iv_valid: bool = adapter(BitFlag())(
        built("B", lambda ctx: ctx.cipher_key != FF_32 and ctx.cipher_iv != FF_16),
    )
    _2: ... = padding(10)
    cipher_key: bytes = field("32s", default=FF_32)
    cipher_iv: bytes = field("16s", default=FF_16)
    _3: ... = padding(16)


@dataclass
class TrapConfig:
    is_valid: bool
    level: int
    port: int
    pin: int


@dataclass
class PartitionRecord(DataStruct):
    offset: int = field("I")
    length: int = field("I")
    type: PartitionType = field("B")
    dbg_skip: bool = field("?", default=False)
    _1: ... = padding(6)
    hash_key_valid: bool = adapter(BitFlag())(
        built("B", lambda ctx: ctx.type == PartitionType.BOOT or ctx.hash_key != FF_32),
    )
    _2: ... = padding(15)
    hash_key: bytes = field("32s", default=FF_32)


def find_partition_index(type: PartitionType):
    return lambda ctx: index(lambda p: p.type == type, ctx.partitions, 255)


@dataclass
class PartitionTable(DataStruct):
    class KeyExport(IntEnum):
        NONE = 0
        LATEST = 1
        BOTH = 2

    rma_w_state: int = field("B", default=0xF0)
    rma_ov_state: int = field("B", default=0xF0)
    e_fwv: int = field("B", default=0)
    _1: ... = padding(1)
    count: int = built("B", lambda ctx: len(ctx.partitions) - 1)
    idx_fw1: int = built("B", find_partition_index(PartitionType.FW1))
    idx_fw2: int = built("B", find_partition_index(PartitionType.FW2))
    idx_var: int = built("B", find_partition_index(PartitionType.VAR))
    idx_mp: int = built("B", find_partition_index(PartitionType.MP))
    _2: ... = padding(1)
    trap_ota: TrapConfig = bitfield("b1p6u1u3u5", TrapConfig, default=0)
    trap_mp: TrapConfig = bitfield("b1p6u1u3u5", TrapConfig, default=0)
    _3: ... = padding(1)
    key_export: KeyExport = field("B", default=KeyExport.BOTH)
    user_data_len: int = built("H", lambda ctx: len(ctx.user_data))
    _4: ... = padding(14)
    partitions: List[PartitionRecord] = repeat(lambda ctx: ctx.count + 1)(subfield())
    user_data: bytes = field(lambda ctx: ctx.user_data_len, default=b"")


@dataclass
class Bootloader(DataStruct):
    entry: EntryHeader = subfield()
    data: bytes = field(lambda ctx: ctx.entry.length, default=b"")
    _1: ... = align(0x20, False, pattern=b"\x00")


@dataclass
class Section(DataStruct):
    # noinspection PyMethodParameters
    def update(ctx: Context):
        section: "Section" = ctx.self
        if section.header.next_offset == 0:
            # calculate next_offset
            size = section.sizeof(**ctx.P.kwargs)
            section.header.next_offset = size

    _0: ... = action(packing(update))
    header: SectionHeader = subfield()
    entry: EntryHeader = subfield()
    data: bytes = field(lambda ctx: ctx.entry.length, default=b"")
    _1: ... = align(0x20, False, pattern=b"\x00")


@dataclass
class Firmware(DataStruct):
    # noinspection PyMethodParameters
    def update(ctx: Context):
        firmware: "Firmware" = ctx.self
        # set next_offset to 0 for all images but the last,
        # to allow calculation by Section.update()
        for section in firmware.sections:
            section.header.next_offset = 0
        firmware.sections[-1].header.next_offset = 0xFFFFFFFF

    _0: ... = action(packing(update))
    fst: FST = subfield()
    sections: List[Section] = repeat(last=header_is_last)(subfield())


@dataclass
class Image(DataStruct):
    # noinspection PyMethodParameters
    def update(ctx: Context):
        image: "Image" = ctx.self
        if image.header.next_offset == 0:
            # calculate next_offset
            size = image.sizeof(**ctx.P.kwargs)
            if ctx.is_first and ctx.is_ota:
                size -= sizeof(image.ota_signature)
            if ctx.is_first:
                size -= sizeof(image.keyblock)
            image.header.next_offset = size
        if ctx.is_first and ctx.is_ota:
            # calculate OTA signature (header hash)
            header = image.header.pack(parent=image)
            if ctx.hash_key:
                image.ota_signature = HMAC(
                    key=ctx.hash_key,
                    msg=header,
                    digestmod=sha256,
                ).digest()
            else:
                image.ota_signature = sha256(header).digest()

    _0: ... = action(packing(update))
    _hash: ... = checksum_start(
        init=lambda ctx: (
            HMAC(ctx.hash_key, digestmod=sha256) if ctx.hash_key else sha256()
        ),
        update=lambda data, obj, ctx: obj.update(data),
        end=lambda obj, ctx: obj.digest(),
    )

    # 'header' hash for firmware images
    ota_signature: Optional[bytes] = cond(lambda ctx: ctx.is_first and ctx.is_ota)(
        field("32s", default=FF_32)
    )
    # keyblock for first sub-image only
    keyblock: Any = cond(lambda ctx: ctx.is_first)(
        switch(lambda ctx: ctx.is_ota)(
            false=(Keyblock, subfield()),
            true=(KeyblockOTA, subfield()),
        )
    )

    header: ImageHeader = subfield()
    data: Any = switch(lambda ctx: ctx.header.type)(
        PARTAB=(PartitionTable, subfield()),
        BOOT=(Bootloader, subfield()),
        # OTA images
        FWHS_S=(Firmware, subfield()),
        FWHS_NS=(Firmware, subfield()),
        FWLS=(Firmware, subfield()),
        XIP=(Firmware, subfield()),
        # something else?
        default=(bytes, field(lambda ctx: ctx.header.length)),
    )

    _1: ... = checksum_end(_hash)
    hash: bytes = checksum_field("Image hash")(field("32s", default=FF_32))
    # align to 0x4000 for images having next_offset, 0x40 otherwise
    # skip offset for non-firmware images
    _2: ... = cond(lambda ctx: ctx.is_ota)(
        align(
            lambda ctx: 0x40 if ctx.header.next_offset == 0xFFFFFFFF else 0x4000,
            pattern=b"\x87",
        )
    )


# noinspection PyMethodParameters,PyAttributeOutsideInit
@dataclass
class Flash(DataStruct):
    def update(ctx: Context):
        flash: "Flash" = ctx.self
        # set next_offset to 0 for all images but the last,
        # to allow calculation by Image.update()
        for image in flash.firmware:
            image.header.idx_pkey = 0
            image.header.next_offset = 0
        flash.firmware[-1].header.next_offset = 0xFFFFFFFF

    def update_offsets(ctx: Context):
        flash: "Flash" = ctx.self
        ptable: PartitionTable = flash.ptable.data
        ctx.boot_offset = ptable.partitions[0].offset
        idx_fw1 = ptable.idx_fw1
        ctx.firmware_offset = ptable.partitions[idx_fw1].offset
        if ptable.partitions[idx_fw1].hash_key_valid:
            ctx.firmware_hash_key = ptable.partitions[idx_fw1].hash_key
        else:
            ctx.firmware_hash_key = None

    _0: ... = action(packing(update))
    calibration: bytes = field("16s", default=FLASH_CALIBRATION)

    _1: ... = alignto(0x20)
    ptable: Image = subfield(
        hash_key=lambda ctx: ctx.hash_key,
        is_ota=False,
        is_first=True,
    )
    _2: ... = action(update_offsets)

    _3: ... = alignto(0x1000)
    system: SystemData = subfield()

    _4: ... = alignto(lambda ctx: ctx.boot_offset)
    boot: Image = subfield(
        hash_key=lambda ctx: ctx.hash_key,
        is_ota=False,
        is_first=True,
    )

    _5: ... = alignto(lambda ctx: ctx.firmware_offset)
    _sum32: ... = checksum_start(
        init=lambda ctx: 0,
        update=lambda data, obj, ctx: obj + sum(data),
        end=lambda obj, ctx: obj & 0xFFFFFFFF,
    )
    firmware: List[Image] = repeat(last=header_is_last)(
        subfield(
            hash_key=lambda ctx: ctx.firmware_hash_key,
            is_ota=True,
            is_first=lambda ctx: ctx.G.tell() == ctx.firmware_offset,
        )
    )
    _6: ... = checksum_end(_sum32)
    sum32: int = checksum_field("FW1 sum32")(field("I", default=0xFFFFFFFF))


@dataclass
class ImageConfig:
    @dataclass
    class Keys:
        decryption: bytes
        keyblock: Dict[str, bytes]
        hash_keys: Dict[str, bytes]
        user_keys: Dict[str, bytes]
        xip_sce_key: bytes
        xip_sce_iv: bytes

        # noinspection PyTypeChecker
        def __post_init__(self):
            self.decryption = bytes.fromhex(self.decryption)
            self.xip_sce_key = bytes.fromhex(self.xip_sce_key)
            self.xip_sce_iv = bytes.fromhex(self.xip_sce_iv)
            self.keyblock = {k: bytes.fromhex(v) for k, v in self.keyblock.items()}
            self.hash_keys = {k: bytes.fromhex(v) for k, v in self.hash_keys.items()}
            self.user_keys = {k: bytes.fromhex(v) for k, v in self.user_keys.items()}

    @dataclass
    class Section:
        name: str
        type: SectionType
        is_boot: bool = False

        # noinspection PyTypeChecker
        def __post_init__(self):
            self.type = str2enum(SectionType, self.type)

    @dataclass
    class Image:
        type: ImageType
        sections: List["ImageConfig.Section"]

        # noinspection PyArgumentList,PyTypeChecker
        def __post_init__(self):
            self.type = str2enum(ImageType, self.type)
            self.sections = [ImageConfig.Section(**v) for v in self.sections]

    keys: Keys
    ptable: Dict[str, PartitionType]
    boot: Section
    fw: List[Image]

    # noinspection PyArgumentList,PyTypeChecker
    def __post_init__(self):
        self.keys = ImageConfig.Keys(**self.keys)
        self.ptable = {k: str2enum(PartitionType, v) for k, v in self.ptable.items()}
        self.boot = ImageConfig.Section(**self.boot)
        self.fw = [ImageConfig.Image(**v) for v in self.fw]


def pad_data(data: bytes, n: int, char: int) -> bytes:
    """Add 'char'-filled padding to 'data' to align to a 'n'-sized block."""
    if len(data) % n == 0:
        return data
    return data + (bytes([char]) * pad_up(len(data), n))


def get_image_config():
    image = {
        "keys": {
            "decryption": "a0d6dae7e062ca94cbb294bf896b9f68cf8438774256ac7403ca4fd9a1c9564f",
            "keyblock": {
                "part_table": "882aa16c8c44a7760aa8c9ab22e3568c6fa16c2afa4f0cea29a10abcdf60e44f",
                "boot": "882aa16c8c44a7760aa8c9ab22e3568c6fa16c2afa4f0cea29a10abcdf60e44f",
            },
            "hash_keys": {
                "part_table": "47e5661335a4c5e0a94d69f3c737d54f2383791332939753ef24279608f6d72b",
                "boot": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
                "ota1": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e5f",
                "ota2": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e5f",
            },
            "user_keys": {
                "boot": "aa0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
                "ota1": "bb0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
                "ota2": "bb0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
            },
            "xip_sce_key": "a0d6dae7e062ca94cbb294bf896b9f68",
            "xip_sce_iv": "94879487948794879487948794879487",
        },
        "ptable": {"boot": "BOOT", "ota1": "FW1", "ota2": "FW2"},
        "boot": {
            "name": "boot.sram",
            "type": "SRAM",
            "is_boot": True,
        },
        "fw": [
            {
                "type": "FWHS_S",
                "sections": [
                    {
                        "name": "fwhs.sram",
                        "type": "SRAM",
                    },
                    {
                        "name": "fwhs.psram",
                        "type": "PSRAM",
                    },
                ],
            },
            {
                "type": "XIP",
                "sections": [
                    {
                        "name": "fwhs.xip_c",
                        "type": "XIP",
                    }
                ],
            },
            {
                "type": "XIP",
                "sections": [
                    {
                        "name": "fwhs.xip_p",
                        "type": "XIP",
                    }
                ],
            },
        ],
    }
    return ImageConfig(**image)


def get_public_key(private: bytes) -> bytes:
    return bytes.fromhex(
        {
            "a0d6dae7e062ca94cbb294bf896b9f68cf8438774256ac7403ca4fd9a1c9564f": "68513ef83e396b12ba059a900f36b6d31d11fe1c5d25eb8aa7c550307f9c2405",
            "882aa16c8c44a7760aa8c9ab22e3568c6fa16c2afa4f0cea29a10abcdf60e44f": "48ad23ddbdac9e65719db7d394d44d62820d19e50d68376774237e98d2305e6a",
        }[private.hex()]
    )


def get_entrypoint(name: str) -> int:
    return {
        "boot.sram": 0x10036100,
        "fwhs.sram": 0x10000480,
        "fwhs.psram": 0,
        "fwhs.xip_c": 0x9B000140,
        "fwhs.xip_p": 0x9B800140,
    }[name]


def build_keyblock(config: ImageConfig, region: str):
    if region in config.keys.keyblock:
        return Keyblock(
            decryption=get_public_key(config.keys.decryption),
            hash=get_public_key(config.keys.keyblock[region]),
        )
    return KeyblockOTA(
        decryption=get_public_key(config.keys.decryption),
    )


def build_section(section: ImageConfig.Section):
    # find entrypoint address
    entrypoint = get_entrypoint(section.name)
    # read the binary image
    if section.name not in ["fwhs.psram"]:
        data = read_data_file(TEST_DATA_URLS[f"raw.{section.name}.bin"])
    else:
        data = b""
    # build EntryHeader
    entry = EntryHeader(
        address=entrypoint,
        entry_table=[entrypoint] if section.type == SectionType.SRAM else [],
    )
    # build Bootloader/Section struct
    if section.is_boot:
        data = pad_data(data, 0x20, 0x00)
        return Bootloader(
            entry=entry,
            data=data,
        )
    return Section(
        header=SectionHeader(type=section.type),
        entry=entry,
        data=data,
    )
