import json
import logging
from typing import List

from common import utilities
from phrase_cipher_enum import PhraseCipher
from to_dict import ToDict

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class PhraseEncoding(ToDict):
    def __init__(self, cipher: PhraseCipher, fields: List[str]):
        self._cipher = cipher
        self._fields = fields

    ## Properties

    @property
    def cipher(self) -> PhraseCipher:
        return self._cipher


    @property
    def fields(self) -> List[str]:
        return self._fields