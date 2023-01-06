#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from ..types import Endianness

ENDIANNESS_DEFAULT = Endianness.DEFAULT


def datastruct(endianness: Endianness):
    def wrap(cls):
        setattr(cls, "_ENDIANNESS", endianness)
        return cls

    return wrap  # @datastruct(...)


def set_default_endianness(endianness: Endianness):
    global ENDIANNESS_DEFAULT
    ENDIANNESS_DEFAULT = endianness


def get_default_endianness():
    return ENDIANNESS_DEFAULT
