#  Copyright (c) Kuba Szczodrzyński 2023-1-20.

from ..types import Config, Endianness

CONFIG = Config(
    endianness=Endianness.DEFAULT,
    padding_pattern=b"\xFF",
    padding_check=False,
    repeat_fill=False,
)


def datastruct_config(
    endianness: Endianness = None,
    padding_pattern: bytes = None,
    padding_check: bool = None,
    repeat_fill: bool = None,
):
    args = {k: v for k, v in locals().items() if v is not None}
    CONFIG.update(args)


def datastruct_get_config():
    return CONFIG
