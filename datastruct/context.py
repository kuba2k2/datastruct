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
        sizing: bool
        root: Optional["Context"]
        hooks: list
        tell: Callable[[], int]
        seek: Union[Callable[[int], int], Callable[[int, int], int]]

        def __str__(self) -> str:
            data = dict(self)
            data["pos"] = self.tell()
            data["op"] = "unpacking" if self.unpacking else "packing"
            data.pop("io", None)
            data.pop("packing", None)
            data.pop("unpacking", None)
            data.pop("sizing", None)
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
        kwargs: dict

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
    self: Any

    def __getattribute__(self, name: str) -> Any:
        # get value from this Context, fallback to value from 'self.self'
        try:
            return super(dict, self).__getattribute__(name)
        except AttributeError:
            try:
                _self = super(dict, self).__getattribute__("self")
                return _self.__getattribute__(name)
            except AttributeError:
                return None

    def __setattr__(self, name: str, value: Any) -> None:
        try:
            # set value in 'self.self' if it has the key;
            # otherwise set it directly in Context
            _self = super(dict, self).__getattribute__("self")
            if isinstance(_self, dict):
                if name in _self:
                    _self[name] = value
                else:
                    super(dict, self).__setattr__(name, value)
                return
            _self.__getattribute__(name)
            _self.__setattr__(name, value)
        except AttributeError:
            super(dict, self).__setattr__(name, value)

    def __getitem__(self, name: str) -> Any:
        return self.__getattribute__(name)

    def __setitem__(self, name: str, value: Any) -> None:
        self.__setattr__(name, value)

    def __str__(self) -> str:
        data = dict(self)
        data.pop("_", None)
        return f"Context({dict2str(data)})"
