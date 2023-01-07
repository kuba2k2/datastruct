#  Copyright (c) Kuba Szczodrzyński 2023-1-7.

from typing import IO, Any, Callable, Optional, Union

from .utils.misc import dict2str


class Container(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return None


class Context(Container):
    class Global(Container):
        io: IO[bytes]
        packing: bool
        unpacking: bool
        env: Container
        root: Optional["Context"]
        hooks: list
        tell: Callable[[], int]
        seek: Union[Callable[[int], int], Callable[[int, int], int]]

        def __str__(self) -> str:
            data = dict(self)
            data["pos"] = self.tell()
            data["op"] = "packing" if self.packing else "unpacking"
            data.pop("io", None)
            data.pop("packing", None)
            data.pop("unpacking", None)
            data.pop("root", None)
            data.pop("tell", None)
            data.pop("seek", None)
            return f"({dict2str(data)})"

    class Params(Container):
        tell: Callable[[], int]
        seek: Union[Callable[[int], int], Callable[[int, int], int]]
        skip: Callable[[int], int]
        i: int
        item: Any

        def __str__(self) -> str:
            data = dict(self)
            data["pos"] = self.tell()
            data.pop("tell", None)
            data.pop("seek", None)
            data.pop("skip", None)
            return f"({dict2str(data)})"

    _: "Context"
    G: Global
    P: Params

    def __str__(self) -> str:
        data = dict(self)
        data.pop("_", None)
        return f"Context({dict2str(data)})"
