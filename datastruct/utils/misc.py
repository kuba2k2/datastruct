#  Copyright (c) Kuba Szczodrzyński 2023-1-6.


def repstr(string, length: int):
    # a significantly faster version of https://stackoverflow.com/a/9021522/9438331
    return (string * (length // len(string) + 1))[0:length]


def pad_up(x: int, n: int) -> int:
    """Return how many bytes of padding is needed to align 'x'
    up to block size of 'n'."""
    return (n - (x % n)) % n


def dict2str(data: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in data.items())
