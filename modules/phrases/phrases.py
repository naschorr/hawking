import json
import os
import random
import re
import logging
import asyncio
from pathlib import Path

import utilities
import dynamo_manager
from string_similarity import StringSimilarity

from discord import errors
from discord.ext import commands
from discord.ext.commands.errors import MissingRequiredArgument

## Config
CONFIG_OPTIONS = utilities.load_module_config(Path(__file__).parent)

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class Phrase:
    def __init__(self, name, message, is_music=False, **kwargs):
        self.name = name
        self.message = message
        self.is_music = is_music
        self.kwargs = kwargs

    def __str__(self):
        return "{} music={} {}".format(self.name, self.is_music, self.kwargs)


class PhraseGroup:
    def __init__(self, name, key, description):
        self.name = name
        self.key = key
        self.description = description
        self.phrases = {}

    def add_phrase(self, phrase):
        if (isinstance(phrase, Phrase)):
            self.phrases[phrase.name] = phrase
        else:
            logger.error("Couldn't add phrase: {}, as it's not a valid Phrase object".format(phrase))


class Phrases(commands.Cog):
    ## Keys
    PHRASES_KEY = "phrases"
    NAME_KEY = "name"
    MESSAGE_KEY = "message"
    IS_MUSIC_KEY = "music"
    HELP_KEY = "help"
    BRIEF_KEY = "brief"
    DESCRIPTION_KEY = "description"


    def __init__(self, hawking, bot, *args, **command_kwargs):
        self.hawking = hawking
        self.bot = bot
        self.phrases_file_extension = CONFIG_OPTIONS.get('phrases_file_extension', '.json')
        self.command_kwargs = command_kwargs
        self.command_names = []
        self.find_command_minimum_similarity = float(CONFIG_OPTIONS.get('find_command_minimum_similarity', 0.5))

        phrases_folder_path = CONFIG_OPTIONS.get('phrases_folder_path')
        if (phrases_folder_path):
            self.phrases_folder_path = Path(phrases_folder_path)
        else:
            self.phrases_folder_path = Path.joinpath(Path(__file__).parent, CONFIG_OPTIONS.get('phrases_folder', 'phrases'))

        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Make sure context is always passed to the callbacks
        self.command_kwargs["pass_context"] = True

        ## The mapping of phrases into groups 
        self.phrase_groups = {}

        ## Compile a regex for filtering non-letter characters
        self.non_letter_regex = re.compile('\W+')

        ## Load and add the phrases
        self.init_phrases()

    ## Properties

    @property
    def speech_cog(self):
        return self.hawking.get_speech_cog()

    @property
    def music_cog(self):
        return self.hawking.get_music_cog()

    ## Methods

    ## Removes all existing phrases when the cog is unloaded
    def cog_unload(self):
        self.remove_phrases()


    ## Searches the phrases folder for .json files that can potentially contain phrases.
    def scan_phrases(self, path_to_scan: Path):
        def is_json_file(file_path: Path):
            return file_path.suffix == self.phrases_file_extension

        phrase_files = []
        for file in os.listdir(path_to_scan):
            file_path = Path(file)
            if(is_json_file(file_path)):
                phrase_files.append(Path.joinpath(path_to_scan, file_path))

        return phrase_files


    ## Builds a PhraseGroup object from a phrase file
    def _build_phrase_group(self, path: Path):
        with open(path) as fd:
            group_raw = json.load(fd)
            name = group_raw.get('name', path.name.split('.')[0])
            key = group_raw.get('key', name)
            description = group_raw.get('description', None)

            return PhraseGroup(name, key, description)


    ## (Attempt to) process a given string down into a searchable string
    def process_string_into_searchable(self, string):
        return self.non_letter_regex.sub(' ', string).lower()


    ## Initialize the phrases available to the bot
    def init_phrases(self):
        phrase_file_paths = self.scan_phrases(self.phrases_folder_path)
        counter = 0
        for phrase_file_path in phrase_file_paths:
            starting_count = counter
            phrase_group = self._build_phrase_group(phrase_file_path)

            for phrase in self.load_phrases(phrase_file_path):
                try:
                    self.add_phrase(phrase)
                    phrase_group.add_phrase(phrase)
                except Exception as e:
                    logger.warning("Skipping...", e)
                else:
                    counter += 1

            ## Ensure we don't add in empty phrase files into the groupings
            if(counter > starting_count):
                self.phrase_groups[phrase_group.key] = phrase_group

                ## Set up a dummy command for the category, to help with the help interface. See help_formatter.py
                ## asyncio.sleep is just a dummy command since commands.Command needs some kind of async callback
                help_command = commands.Command(self._create_noop_callback(), name=phrase_group.key, hidden=True, no_pm=True)
                self.bot.add_command(help_command)
                self.command_names.append(phrase_group.key) # Keep track of the 'parent' commands for later use

        logger.info("Loaded {} phrase{}.".format(counter, "s" if counter != 1 else ""))
        return counter


    ## Unloads all phrase commands, then reloads them from the phrases.json file
    def reload_phrases(self):
        self.remove_phrases()
        return self.init_phrases()


    ## Load phrases from json into a list of phrase objects
    def load_phrases(self, path: Path):
        ## Insert source[key] (if it exists) into target[key], else insert a default string
        def insert_if_exists(target, source, key, default=None):
            if(key in source):
                target[key] = source[key]
            return target

        phrases = []
        with open(path) as fd:
            for phrase_raw in json.load(fd)[self.PHRASES_KEY]:
                try:
                    message = phrase_raw[self.MESSAGE_KEY]

                    ## Todo: make this less ugly
                    kwargs = {}
                    help_value = phrase_raw.get(self.HELP_KEY)  # fallback for the help submenus
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.HELP_KEY)
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.BRIEF_KEY, help_value)

                    ## Attempt to populate the description kwarg, but if it isn't available, then try and parse the
                    ## message down into something usable instead.
                    if (self.DESCRIPTION_KEY in phrase_raw):
                        kwargs[self.DESCRIPTION_KEY] = phrase_raw[self.DESCRIPTION_KEY]
                    else:
                        kwargs[self.DESCRIPTION_KEY] = self.process_string_into_searchable(message)

                    phrase_name = phrase_raw[self.NAME_KEY]
                    phrase = Phrase(
                        phrase_name,
                        message,
                        phrase_raw.get(self.IS_MUSIC_KEY, False),
                        **kwargs
                    )
                    phrases.append(phrase)
                    self.command_names.append(phrase_name)
                except Exception as e:
                    logger.warning("Error loading {} from {}. Skipping...".format(phrase_raw, fd), e)

        ## Todo: This doesn't actually result in the phrases in the help menu being sorted?
        return sorted(phrases, key=lambda phrase: phrase.name)


    ## Unloads the preset phrases from the bot's command list
    def remove_phrases(self):
        for name in self.command_names:
            self.bot.remove_command(name)
        self.command_names = []
        self.phrase_groups = {} # yay garbage collection

        return True


    ## Add a phrase command to the bot's command list
    def add_phrase(self, phrase):
        if(not isinstance(phrase, Phrase)):
            raise TypeError("{} not instance of Phrase.".format(phrase))

        ## Manually build command to be added
        command = commands.Command(
            self._create_phrase_callback(phrase.message, phrase.is_music),
            name = phrase.name,
            **phrase.kwargs,
            **self.command_kwargs
        )
        ## Ensure that this command is linked to the Phrases cog
        command.cog = self

        self.bot.add_command(command)


    def _create_noop_callback(self):
        '''
        Build an async noop callback. This is used as a dummy callback for the help commands that make up the command
        categories
        '''

        async def _noop_callback(ctx):
            await asyncio.sleep(0)

        return _noop_callback


    ## Build a dynamic callback to invoke the bot's say method
    def _create_phrase_callback(self, message, is_music=False):
        ## Create a callback for speech._say
        async def _phrase_callback(self, ctx):
            ## Attempt to get a target channel
            try:
                target = ctx.message.mentions[0]
            except:
                target = None

            await self.speech_cog._say(ctx, message, target_member = target, ignore_char_limit = True)

        ## Create a callback for music.music
        # async def _music_callback(self, ctx):
        #     music_cog = self.music_cog
        #     await music_cog.music(ctx, message, ignore_char_limit=True)

        ## Return the appropriate callback
        # if(is_music):
        #     return _music_callback
        # else:
        return _phrase_callback


    ## Says a random phrase from the added phrases
    @commands.command(no_pm=True)
    async def random(self, ctx):
        """Says a random clip from the list of clips."""

        random_clip = random.choice(self.command_names)
        command = self.bot.get_command(random_clip)
        await command.callback(self, ctx)


    ## Scores a given string (message) based on how many of it's words exist in another string (description)
    def _calc_substring_score(self, message, description):
        ## Todo: shrink instances of repeated letters down to a single letter in both message and description
        ##       (ex. yeeeee => ye or reeeeeboot => rebot)

        message_split = message.split(' ')
        word_frequency = 0
        for word in message_split:
            if (word in description.split(' ')):
                word_frequency += 1

        return word_frequency / len(message_split)


    ## Attempts to find the command whose description text most closely matches the provided message
    @commands.command(no_pm=True)
    async def find(self, ctx, *, search_text = None):
        '''Find phrases that are similar to the search text'''

        ## This method isn't ideal, as it breaks the command's signature. However it's the least bad option until
        ## Command.error handling doesn't always call the global on_command_error
        if (search_text is None):
            await self.find_error(ctx, MissingRequiredArgument(ctx.command.params['search_text']))
            return

        ## Strip all non alphanumeric and non whitespace characters out of the message
        message = ''.join(char for char in search_text.lower() if (char.isalnum() or char.isspace()))

        most_similar_command = (None, 0)
        for phrase_group in self.phrase_groups.values():
            for phrase in phrase_group.phrases.values():
                ## Todo: Maybe look into filtering obviously bad descriptions from the calculation somehow?
                ##       A distance metric might be nice, but then if I could solve that problem, why not just use that
                ##       distance in the first place and skip the substring check?

                description = phrase.kwargs.get(self.DESCRIPTION_KEY)
                if (not description):
                    continue

                ## Build a weighted distance using a traditional similarity metric and the previously calculated word
                ## frequency as well as the similarity of the actual string that invokes the phrase
                distance =  (self._calc_substring_score(message, description) * 0.5) + \
                            (StringSimilarity.similarity(description, message) * 0.3) + \
                            (StringSimilarity.similarity(message, phrase.name) * 0.2)

                if (distance > most_similar_command[1]):
                    most_similar_command = (phrase, distance)

        if (most_similar_command[1] > self.find_command_minimum_similarity):
            command = self.bot.get_command(most_similar_command[0].name)
            await command.callback(self, ctx)
        else:
            await ctx.send("I couldn't find anything close to that, sorry <@{}>.".format(ctx.message.author.id))

    
    @find.error
    async def find_error(self, ctx, error):
        '''
        Find command error handler. Addresses some common error scenarios that on_command_error doesn't really help with
        '''
        
        if (isinstance(error, MissingRequiredArgument)):
            output_raw = "Sorry <@{}>, but I need something to search for! Why not try: **{}find {}**?"
            await ctx.send(output_raw.format(
                ctx.message.author.id,
                CONFIG_OPTIONS.get("activation_str"),
                random.choice(self.command_names)
            ))


def main():
    return [Phrases, True]
