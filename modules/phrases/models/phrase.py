import logging
from pathlib import Path

from common import utilities
from models.phrase_encoding import PhraseEncoding

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class Phrase:
    def __init__(self, name: str, message: str, encoding: PhraseEncoding, **kwargs):
        self.name = name
        self.message = message
        self.encoding = encoding
        self._encoded = False
        self.help = kwargs.get('help')
        self.brief = kwargs.get('brief')
        self.description = kwargs.get('description')
        self.is_music = kwargs.get('is_music', False)
        self.kwargs = kwargs


    def __str__(self):
        return "{} - {}".format(self.name, self.kwargs)

    ## Properties

    @property
    def encoded(self) -> bool:
        return self._encoded
