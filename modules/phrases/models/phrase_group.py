import copy
import json
import logging
from pathlib import Path
from typing import List

from common.logging import Logging
from models.phrase import Phrase
from to_dict import ToDict

## Logging
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class PhraseGroup(ToDict):
    def __init__(self, name: str, key: str, description: str, path: Path, **kwargs):
        self.name = name
        self.key = key
        self.description = description
        self.path = path
        self.kwargs = kwargs

        self.phrases = {}

    ## Methods

    def add_phrase(self, phrase: Phrase):
        self.phrases[phrase.name] = phrase


    def add_all_phrases(self, phrases: List[Phrase]):
        for phrase in phrases:
            self.add_phrase(phrase)


    def to_dict(self) -> dict:
        data = super().to_dict()

        del data['path']
        del data['kwargs']

        for key, value in self.kwargs.items():
            data[key] = value

        data['phrases'] = [phrase.to_dict() for phrase in self.phrases.values()]

        return data
