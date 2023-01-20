#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

import struct

FMT_ENDIAN = "@=<>!"
FMT_SPEC = "cbB?hHiIlLqQnNefds"
ARRAYS = (list, tuple)
EXCEPTIONS = (ValueError, TypeError, AttributeError, struct.error)
BYTES = (bytes, bytearray)
