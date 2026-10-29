from abc import ABCMeta, abstractmethod
from typing import Dict


class CommandItem(metaclass=ABCMeta):
    @abstractmethod
    def to_json(self) -> Dict:
        return


    @abstractmethod
    def build_primary_key(self) -> str:
        return
