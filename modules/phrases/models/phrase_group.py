import logging
from pathlib import Path
from typing import List

from common import utilities
from models.phrase import Phrase

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class PhraseGroup:
    def __init__(self, name: str, key: str, description: str, path: Path, **kwargs):
        self.name = name
        self.key = key
        self.description = description
        self.path = path
        self.kwargs = kwargs

        self.phrases = {}


    def add_phrase(self, phrase: Phrase):
        self.phrases[phrase.name] = phrase


    def add_all_phrases(self, phrases: List[Phrase]):
        for phrase in phrases:
            self.add_phrase(phrase)
