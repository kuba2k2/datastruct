#  Copyright (c) Kuba Szczodrzyński 2023-1-3.

from ..types import Context, Endianness, Value
from .const import FMT_ENDIAN, FMT_SPEC
from .context import evaluate


def fmt_check(fmt: Value[str]) -> None:
    """
    Check the passed format specifier.
    Do nothing for lambdas; that needs to be checked later on.
    """
    if callable(fmt):
        return
    orig_fmt = fmt
    if fmt[0] in FMT_ENDIAN:
        fmt = fmt[1:]
    count = fmt[:-1]
    spec = fmt[-1]
    if spec not in FMT_SPEC:
        raise ValueError(f"Format specifier '{orig_fmt}' is invalid or unsupported")
    if count and not count.isnumeric():
        raise ValueError(f"Format specifier '{orig_fmt}' has non-numeric count")


def fmt_evaluate(ctx: Context, fmt_val: Value[str], endianness: Endianness) -> str:
    """
    First evaluate(), then fmt_check() the given format (if it's a lambda).
    Set endianness if not set already.

    :return: a valid format specifier, with endianness applied
    """
    fmt = evaluate(ctx, fmt_val)
    if callable(fmt_val):
        fmt_check(fmt)
    if fmt[0] not in FMT_ENDIAN:
        fmt = endianness.value + fmt
    return fmt
