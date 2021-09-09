import json
import logging
import os
import re
from pathlib import Path
from typing import List

from common import utilities
from models.phrase import Phrase
from models.phrase_group import PhraseGroup
from models.phrase_encoding import PhraseEncoding
from phrase_encoder_decoder import PhraseEncoderDecoder

## Config
CONFIG_OPTIONS = utilities.load_module_config(Path(__file__).parent)

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class PhraseFileManager:
    def __init__(self):
        self.phrases_file_extension = CONFIG_OPTIONS.get('phrases_file_extension', '.json')
        self.non_letter_regex = re.compile('\W+')   # Compile a regex for filtering non-letter characters

        phrases_folder_path = CONFIG_OPTIONS.get('phrases_folder_path')
        if (phrases_folder_path):
            self.phrases_folder_path = Path(phrases_folder_path)
        else:
            self.phrases_folder_path = Path.joinpath(Path(__file__).parent, CONFIG_OPTIONS.get('phrases_folder', 'phrases'))


    def discover_phrase_groups(self, path_to_scan: Path) -> List[Path]:
        '''Searches the phrases folder for .json files that can potentially contain phrase groups & phrases'''

        phrase_files = []
        for file in os.listdir(path_to_scan):
            file_path = Path(file)
            if(file_path.suffix == self.phrases_file_extension):
                phrase_files.append(Path.joinpath(path_to_scan, file_path))

        return phrase_files


    def _build_phrase_encoding(self, phrase_json: dict) -> PhraseEncoding:
        '''Builds a PhraseEncoding object from raw JSON'''

        if ('cipher' in phrase_json and 'fields' in phrase_json):
            return PhraseEncoding(phrase_json['cipher'], phrase_json['fields'])
        else:
            return None


    def _build_phrases(self, phrases_json: dict, decode = True) -> List[Phrase]:
        '''
        Given a JSON dict representing an unparsed PhraseGroup's list of Phrases, build a list of Phrase objects from
        it, and return that list
        '''

        ## Insert source[key] (if it exists) into target[key], else insert a default string
        def insert_if_exists(target, source, key, default=None):
            if(key in source):
                target[key] = source[key]
            return target
        
        phrases = []
        for phrase_raw in phrases_json:
            try:
                name = phrase_raw['name']
                message = phrase_raw['message']

                if ('encoding' in phrase_raw != None):
                    encoding = self._build_phrase_encoding(phrase_raw['encoding'])
                else:
                    encoding = None

                ## Todo: make this less ugly
                kwargs = {}
                help_value = phrase_raw.get('help')  # fallback for the help submenus
                kwargs = insert_if_exists(kwargs, phrase_raw, 'help')
                kwargs = insert_if_exists(kwargs, phrase_raw, 'brief', help_value)

                ## Attempt to populate the description kwarg, but if it isn't available, then try and parse the
                ## message down into something usable instead.
                if ('description' in phrase_raw):
                    kwargs['description'] = phrase_raw['description']
                else:
                    kwargs['description'] = self.non_letter_regex.sub(' ', message).lower()
                    
                    ## If the message attribute is encoded, then the derived description should also be encoded.
                    if ('message' in encoding.fields):
                        encoding.fields.append('description')
                
                kwargs['is_music'] = phrase_raw.get('music', False),

                phrase = Phrase(
                    name,
                    message,
                    encoding,
                    **kwargs
                )

                ## Decode the phrase!
                if (decode and phrase.encoded):
                    PhraseEncoderDecoder.decode(phrase)

                phrases.append(phrase)
            except Exception as e:
                logger.warn(f"Error loading phrase '{phrase_raw['name']}'. Skipping...", e)
                continue

        return sorted(phrases, key=lambda phrase: phrase.name)


    def load_phrase_group(self, path: Path, decode = True) -> PhraseGroup:
        '''
        Loads a PhraseGroup from a given phrase file json path.

        Traverses the json file, creates a PhraseGroup, populates the metadata, and then traverses the phrase objects.
        Phrases are built from that data, and added to the PhraseGroup. The completed PhraseGroup is returned.
        '''

        with open(path) as fd:
            data = json.load(fd)

            try:
                phrase_group_name = None
                phrase_group_key = None
                phrase_group_description = None
                kwargs = {}

                ## Loop over the key-values in the json file. Handle each expected pair appropriately, and store
                ## unexpected pairs in the kwargs variable. Unexpected data is fine, but it needs to be preserved so
                ## that re-saved files will be equivalent to the original file.
                for key, value in data.items():
                    if (key == 'name'):
                        phrase_group_name = value
                    elif (key == 'key'):
                        phrase_group_key = value
                    elif  (key == 'description'):
                        phrase_group_description = value
                    elif (key == 'phrases'):
                        phrases = self._build_phrases(value, decode)
                    else:
                        kwargs[key] = value

                ## With the loose pieces processed, make sure the required pieces exist.
                if (phrase_group_name == None or phrase_group_key == None or phrase_group_description == None or len(phrases) == 0):
                    logger.warning(f"Error loading phrase group '{phrase_group_name}', from '{path}'. Missing 'name', 'key', 'description', or non-zero length 'phrases' list. Skipping...")
                    return None

                ## Construct the PhraseGroup, and add the Phrases to it.
                phrase_group = PhraseGroup(phrase_group_name, phrase_group_key, phrase_group_description, path, **kwargs)
                phrase_group.add_all_phrases(phrases)

                return phrase_group
            except Exception as e:
                logger.warning(f"Error loading phrase group '{phrase_group_name}' from '{path}''. Skipping...", e)
                return None


    def save_phrase_group(self, path: Path, phrase_group: PhraseGroup):
        pass