import threading
from typing import Type
from abc import ABC, abstractmethod

class Singleton(type):
    """
    Create a class which only init once
    Instruction:
        class foo(metaclass=Singleton)
    """
    _instance = {}
    _lock = threading.Lock()
    def __call__(cls, *args, **kwds):
        if cls not in cls._instance:
            with cls._lock:
                if cls not in cls._instance:
                    instance = super().__call__(*args, **kwds)
                    cls._instance[cls] = instance
        return cls._instance[cls]

from enum import Enum

class Custom_Enum(Enum):
    @classmethod
    def keys(cls) -> list:
        return cls._member_names_

    @classmethod
    def values(cls) -> list:
        return list(cls._value2member_map_.keys())

    @classmethod
    def list(cls) -> list:
        return list(cls)

    @classmethod
    def dict(cls) -> dict:
        return cls._member_map_

    @classmethod
    def index(cls, item: Type["Enum | str"]) -> int:
        """
        :item: can be member or name
        """
        if type(item) != str:
            item = item.name
        return cls._member_names_.index(item)

    @classmethod
    def get(cls, index: int):
        """
        Return value from index
        """
        return cls.values()[index]