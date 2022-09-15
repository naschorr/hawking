import json
import os
import random
import re
import logging
import asyncio
from pathlib import Path
from typing import Dict, List

from common import utilities
from common.database import dynamo_manager
from common.string_similarity import StringSimilarity
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer
from phrase_file_manager import PhraseFileManager
from models.phrase_group import PhraseGroup
from models.phrase import Phrase

from discord import errors
from discord.ext import commands
from discord.ext.commands.errors import MissingRequiredArgument

## Config
CONFIG_OPTIONS = utilities.load_module_config(Path(__file__).parent)

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class Phrases(DiscoverableCog):
    def __init__(self, hawking, bot, *args, **command_kwargs):
        super().__init__(*args, **command_kwargs)

        self.phrase_file_manager = PhraseFileManager()
        self.dynamo_db = dynamo_manager.DynamoManager()

        self.hawking = hawking
        self.bot = bot
        self.command_kwargs = command_kwargs
        self.command_names: List[str] = []  # All command names
        self.phrase_command_names: List[str] = []
        self.find_command_minimum_similarity = float(CONFIG_OPTIONS.get('find_command_minimum_similarity', 0.5))
        self.phrase_groups: Dict[str, PhraseGroup] = {}
        self.phrases_folder_path = self.phrase_file_manager.phrases_folder_path

        ## Make sure context is always passed to the callbacks
        self.command_kwargs["pass_context"] = True

        ## Load and add the phrases
        self.init_phrases()
        self.successful = True

    ## Properties

    @property
    def speech_cog(self):
        ## todo: use injected dependency
        return self.hawking.get_speech_cog()

    @property
    def music_cog(self):
        return self.hawking.get_music_cog()

    ## Methods

    ## Removes all existing phrases when the cog is unloaded
    def cog_unload(self):
        self.remove_phrases()


    ## Builds a PhraseGroup object from a phrase file
    def _build_phrase_group(self, path: Path):
        with open(path) as fd:
            group_raw = json.load(fd)
            name = group_raw.get('name', path.name.split('.')[0])
            key = group_raw.get('key', name)
            description = group_raw.get('description', None)

            return PhraseGroup(name, key, description, path)


    def init_phrases(self):
        '''Initialize the phrases available to the bot'''

        phrase_group_file_paths = self.phrase_file_manager.discover_phrase_groups(self.phrases_folder_path)
        counter = 0
        for phrase_file_path in phrase_group_file_paths:
            starting_count = counter
            phrase_group = self.phrase_file_manager.load_phrase_group(phrase_file_path)

            phrase: Phrase
            for phrase in phrase_group.phrases.values():
                try:
                    self.add_phrase(phrase)
                    self.command_names.append(phrase.name)
                    self.phrase_command_names.append(phrase.name)
                except Exception as e:
                    logger.warning("Skipping...", e)
                else:
                    counter += 1

            ## Ensure we don't add in empty phrase files into the groupings
            ## todo: this isn't necessary any more, is it?
            if(counter > starting_count):
                self.phrase_groups[phrase_group.key] = phrase_group

                ## Set up a dummy command for the category, to help with the help interface. See help_command.py
                ## asyncio.sleep is just a dummy command since commands.Command needs some kind of async callback
                help_command = commands.Command(self._create_noop_callback(), name=phrase_group.key, hidden=True, no_pm=True)
                self.bot.add_command(help_command)
                self.command_names.append(phrase_group.key) # Keep track of the 'parent' commands for later use

        logger.info("Loaded {} phrase{}.".format(counter, "s" if counter != 1 else ""))
        return counter


    def reload_phrases(self):
        '''Unloads all phrase commands from the bot, then reloads all of the phrases, and reapplies them to the bot'''

        self.remove_phrases()
        return self.init_phrases()


    def remove_phrases(self):
        '''Unloads the preset phrases from the bot's command list.'''

        for name in self.command_names:
            self.bot.remove_command(name)
        self.command_names = []
        self.phrase_command_names = []
        self.phrase_groups = {} # yay garbage collection

        return True


    def add_phrase(self, phrase: Phrase):
        '''Adds a phrase command to the bot's command list.'''

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


    def _create_phrase_callback(self, message, is_music=False):
        '''Build a dynamic callback to invoke the bot's say method'''

        ## Create a callback for speech._say
        async def _phrase_callback(self, *args):
            ## Looks like discord.py v2.0 changed how context is passed, thus this slightly clunky way of getting it.
            ctx = args[0] or None
            if (ctx is None or not isinstance(ctx, commands.context.Context)):
                logger.error("No context provided to phrase callback")
                return

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


    @commands.command(no_pm=True)
    async def random(self, ctx):
        """Says a random phrase from the list of phrases."""

        random_phrase = random.choice(self.phrase_command_names)
        command = self.bot.get_command(random_phrase)
        await command.callback(self, ctx)


    def _calc_substring_score(self, message, description):
        '''Scores a given string (message) based on how many of it's words exist in another string (description)'''

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

                description = phrase.kwargs.get('description')
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
                random.choice(self.phrase_command_names)
            ))


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(Phrases)
