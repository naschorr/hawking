import json
import logging
from typing import List

from hawking.core.services.logging.logging_service import Logging
from addons.phrases.phrase_cipher_enum import PhraseCipher
from addons.phrases.to_dict import ToDict

## Logging
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))

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
