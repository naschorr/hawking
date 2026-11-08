import argparse
import logging
import sys
from pathlib import Path
from typing import Callable

from hawking.core.services.logging.logging_service import Logging
from hawking.configuration import load_hawking_config
from addons.phrases.phrases_config import PhrasesConfig

## Logging
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class PhraseTools:
    @staticmethod
    def _process_phrases(phrase_operation: Callable, config: PhrasesConfig):
        phrase_file_manager = PhraseFileManager(config)

        phrases_folder_path = phrase_file_manager.phrases_folder_path
        phrase_group_paths = phrase_file_manager.discover_phrase_groups(phrases_folder_path)

        path: Path
        for path in phrase_group_paths:
            ## Load the phrase group
            try:
                phrase_group: PhraseGroup = phrase_file_manager.load_phrase_group(path, False)
            except Exception as e:
                LOGGER.error(f'Error loading phrase group from {path}', exc_info=e)
                continue

            ## Manipulate each of the loaded phrases
            phrase: Phrase
            for phrase in phrase_group.phrases.values():
                try:
                    phrase_operation(phrase)
                except Exception as e:
                    LOGGER.error(f'Error encoding phrase {phrase}', exc_info=e)
                    continue

            ## Save the phrase group (containing the modified phrases)
            phrase_file_manager.save_phrase_group(path, phrase_group)


    @staticmethod
    def encode(config: PhrasesConfig):
        PhraseTools._process_phrases(PhraseEncoderDecoder.encode, config)


    @staticmethod
    def decode(config: PhrasesConfig):
        PhraseTools._process_phrases(PhraseEncoderDecoder.decode, config)


if (__name__ == '__main__'):
    parser = argparse.ArgumentParser(description='Phrase File Tools')
    parser.add_argument(
        '--encode',
        dest='operation',
        action='store_const',
        const=PhraseTools.encode,
        help="Encodes all phrase files's phrases according to their own encoding schema."
    )
    parser.add_argument(
        '--decode',
        dest='operation',
        action='store_const',
        const=PhraseTools.decode,
        help="Decodes all phrase files's phrases according to their own encoding schema."
    )

    args = parser.parse_args()

    try:
        operation = args.operation
    except Exception as e:
        LOGGER.error("Missing required '--encode' or '--decode' argument.", exc_info=e)

    config_data = load_hawking_config().addons.get("phrases", {})
    config = PhrasesConfig.model_validate(config_data)
    operation(config)
