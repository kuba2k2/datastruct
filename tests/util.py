#  Copyright (c) Kuba Szczodrzyński 2024-10-12.


def read_data_file(name_or_url: str, gzipped: bool = False) -> bytes:
    if name_or_url.startswith("http"):
        import requests

        print(f"Downloading data from '{name_or_url}'")
        with requests.get(name_or_url) as r:
            data = r.content
    else:
        from pathlib import Path

        print(f"Reading data from '{name_or_url}'")
        path = Path(__file__).with_name(name_or_url)
        data = path.read_bytes()

    if gzipped:
        import gzip

        return gzip.decompress(data)
    return data
