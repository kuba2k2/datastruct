#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from ..types import Config, Endianness

CONFIG = Config(
    endianness=Endianness.DEFAULT,
    padding_pattern=b"\xFF",
    padding_check=False,
)


def datastruct(
    endianness: Endianness = None,
    padding_pattern: bytes = None,
    padding_check: bool = None,
):
    args = {k: v for k, v in locals().items() if v is not None}

    def wrap(cls):
        setattr(cls, "_CONFIG", args)
        return cls

    return wrap  # @datastruct(...)


def datastruct_config(
    endianness: Endianness = None,
    padding_pattern: bytes = None,
    padding_check: bool = None,
):
    args = {k: v for k, v in locals().items() if v is not None}
    CONFIG.update(args)


def datastruct_get_config():
    return CONFIG
