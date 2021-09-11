import copy
import logging
from pathlib import Path

from common import utilities
from models.phrase_encoding import PhraseEncoding
from to_dict import ToDict

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class Phrase(ToDict):
    def __init__(self, name: str, message: str, encoding: PhraseEncoding, **kwargs):
        self.name = name
        self.message = message
        self.encoding = encoding
        self.encoded = kwargs.get('encoded', False)
        self.help = kwargs.get('help')
        self.brief = kwargs.get('brief')
        self.description = kwargs.get('description')
        self._derived_description = kwargs.get('derived_description', False)
        self.is_music = kwargs.get('is_music', False)
        self.kwargs = kwargs


    def __str__(self):
        return "{} - {}".format(self.name, self.__dict__)

    ## Methods

    def to_dict(self) -> dict:
        data = super().to_dict()

        del data['kwargs']

        if (self.encoded != True):
            del data['encoded']
        if (self.help is None):
            del data['help']
        if (self.brief is None):
            del data['brief']
        if (not self.is_music):
            del data['is_music']

        if (self.encoding is not None):
            data['encoding'] = self.encoding.to_dict()

            if ('description' not in self.encoding.fields):
                del data['description']
        else:
            del data['encoding']
        
        if (self._derived_description and 'description' in data):
            del data['description']

        return data
