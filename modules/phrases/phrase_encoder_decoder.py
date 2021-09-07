import codecs
import logging
from pathlib import Path

from common import utilities
from phrase_cipher_enum import PhraseCipher
from models.phrase import Phrase

## Config
CONFIG_OPTIONS = utilities.load_module_config(Path(__file__).parent)

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class PhraseEncoderDecoder:
    CIPHER: PhraseCipher = PhraseCipher.ROT13

    @staticmethod
    def decode(phrase: Phrase):
        '''
        Decodes this Phrase, provided that its 'encoded' property is True, and an encoding schema set on it. Works in
        place, nothing is returned.
        '''

        if (phrase.encoding != None and phrase.encoded == False):
            return

        if (phrase.encoding.cipher == PhraseEncoderDecoder.CIPHER and len(phrase.encoding.fields) > 0):
            for key, value in vars(phrase).items():
                if (key in phrase.encoding.fields):
                    setattr(phrase, key, codecs.decode(value, PhraseEncoderDecoder.CIPHER))

        phrase._encoded = False


    @staticmethod
    def encode(phrase: Phrase):
        '''
        Encodes this Phrase, provided that its 'encoded' property is False and an encoding schema has been set. Works
        in place, nothing is returned.
        '''

        if (phrase.encoding != None and phrase.encoded == True):
            return

        if (phrase.encoding.cipher == PhraseEncoderDecoder.CIPHER and len(phrase.encoding.fields) > 0):
            for key, value in vars(phrase).items():
                if (key in phrase.encoding.fields):
                    setattr(phrase, key, codecs.encode(value, PhraseEncoderDecoder.CIPHER))

        phrase._encoded = True
