#  Copyright (c) Kuba Szczodrzyński 2023-11-23.

from dataclasses import MISSING, dataclass

from macaddress import MAC

from datastruct import DataStruct
from datastruct.adapters.network import mac_field
from datastruct.fields import adapter, field, text
from datastruct.types import FormatType


def hexfield(fmt: FormatType, sep: str = "", *, default=..., default_factory=MISSING):
    return adapter(
        encode=lambda value, ctx: bytes.fromhex(value),
        decode=lambda value, ctx: value.hex(),
    )(field(fmt, default=default, default_factory=default_factory))


@dataclass
class RiData(DataStruct):
    format: str = text(2)
    mfr_id: str = text(4)
    factory_code: str = text(2)
    hw_version: str = text(12)
    ics: str = text(2)
    yp_serial_num: str = text(16)
    clei_code: str = text(10)
    mnemonic: str = text(8)
    prog_date: str = text(6)
    mac_address: MAC = mac_field()
    device_id_pref: str = hexfield(2)
    sw_image: str = hexfield(2)
    onu_mode: str = hexfield(2)
    mnemonic2: str = text(4)
    password: str = hexfield(10)
    g894_serial: str = hexfield(4)
    hw_configuration: str = hexfield(8)
    part_number: str = text(12)
    spare4: str = hexfield(12)
    checksum: str = hexfield(2)
    inservice_reg: str = hexfield(2)
    user_name: str = text(16)
    user_password: str = text(8)
    mgnt_user_name: str = text(16)
    mgnt_user_password: str = text(8)
    ssid1_name: str = text(16)
    ssid1_password: str = text(8)
    ssid2_name: str = text(16)
    ssid2_password: str = text(8)
    operator_id: str = text(4)
    slid: str = hexfield(16)
    country_id: str = text(2)
    spare_5: str = hexfield(6)
    checksum1: str = hexfield(2)
    spare6: str = hexfield(2)
