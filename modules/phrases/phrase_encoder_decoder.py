import codecs
import logging
from pathlib import Path

from common.configuration import Configuration
from common.logging import Logging
from modules.phrases.phrase_cipher_enum import PhraseCipher
from modules.phrases.models.phrase import Phrase

## Config & logging
CONFIG_OPTIONS = Configuration.load_config(Path(__file__).parent)
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class PhraseEncoderDecoder:
    CIPHER: PhraseCipher = PhraseCipher.ROT13

    @staticmethod
    def decode(phrase: Phrase):
        '''
        Decodes this Phrase, provided that its 'encoded' property is True, and an encoding schema set on it. Works in
        place, nothing is returned.
        '''

        if (not phrase.encoding or phrase.encoded == False):
            return

        if (phrase.encoding.cipher == PhraseEncoderDecoder.CIPHER.value and len(phrase.encoding.fields) > 0):
            for key, value in vars(phrase).items():
                if (key in phrase.encoding.fields):
                    decoded = codecs.decode(value, PhraseEncoderDecoder.CIPHER.value)
                    setattr(phrase, key, decoded)

        phrase.encoded = False


    @staticmethod
    def encode(phrase: Phrase):
        '''
        Encodes this Phrase, provided that its 'encoded' property is False and an encoding schema has been set. Works
        in place, nothing is returned.
        '''

        if (not phrase.encoding or phrase.encoded == True):
            return

        if (phrase.encoding.cipher == PhraseEncoderDecoder.CIPHER.value and len(phrase.encoding.fields) > 0):
            for key, value in vars(phrase).items():
                if (key in phrase.encoding.fields):
                    encoded = codecs.encode(value, PhraseEncoderDecoder.CIPHER.value)
                    setattr(phrase, key, encoded)

        phrase.encoded = True
