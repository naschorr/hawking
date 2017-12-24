import json
import os
import random
from discord import errors
from discord.ext import commands

import utilities
import dynamo_helper

## Config
CONFIG_OPTIONS = utilities.load_config()


class Phrase:
    def __init__(self, name, message, is_music=False, **kwargs):
        self.name = name
        self.message = message
        self.is_music = is_music
        self.kwargs = kwargs


    def __str__(self):
        return "{} music={} {}".format(self.name, self.is_music, self.kwargs)


class Phrases:
    ## Keys
    PHRASES_KEY = "phrases"
    PHRASES_FILE_EXTENSION_KEY = "phrases_file_extension"
    PHRASES_FOLDER_KEY = "phrases_folder"
    PHRASES_FOLDER_PATH_KEY = "phrases_folder_path"
    NAME_KEY = "name"
    MESSAGE_KEY = "message"
    IS_MUSIC_KEY = "music"
    HELP_KEY = "help"
    BRIEF_KEY = "brief"
    DESCRIPTION_KEY = "description"

    ## Defaults
    PHRASES_FILE_EXTENSION = CONFIG_OPTIONS.get(PHRASES_FILE_EXTENSION_KEY, ".json")
    PHRASES_FOLDER = CONFIG_OPTIONS.get(PHRASES_FOLDER_KEY, "phrases")
    PHRASES_FOLDER_PATH = CONFIG_OPTIONS.get(PHRASES_FOLDER_PATH_KEY, os.sep.join([utilities.get_root_path(), PHRASES_FOLDER]))


    def __init__(self, hawking, bot, phrases_folder_path=None, **command_kwargs):
        self.hawking = hawking
        self.bot = bot
        self.phrases_file_extension = self.PHRASES_FILE_EXTENSION
        self.phrases_folder_path = phrases_folder_path or self.PHRASES_FOLDER_PATH
        self.command_kwargs = command_kwargs
        self.command_names = []

        self.dynamo_db = dynamo_helper.DynamoHelper()

        ## Make sure context is always passed to the callbacks
        self.command_kwargs["pass_context"] = True

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
    def __unload(self):
        self.remove_phrases()


    ## Searches the phrases folder for .json files that can potentially contain phrases.
    def scan_phrases(self, path_to_scan):
        def is_phrase_file(file_path):
            to_check = file_path[-len(self.phrases_file_extension):]
            return (to_check == self.phrases_file_extension)

        phrase_files = []
        for file in os.listdir(path_to_scan):
            if(is_phrase_file(file)):
                phrase_files.append(os.sep.join([path_to_scan, file]))

        return phrase_files


    ## Initialize the phrases available to the bot
    def init_phrases(self):
        phrase_file_paths = self.scan_phrases(self.phrases_folder_path)

        counter = 0
        for phrase_file_path in phrase_file_paths:
            for phrase in self.load_phrases(phrase_file_path):
                try:
                    self.add_phrase(phrase)
                except Exception as e:
                    utilities.debug_print(e, "Skipping...", debug_level=2)
                else:
                    counter += 1

        print("Loaded {} phrase{}.".format(counter, "s" if counter != 1 else ""))
        return counter


    ## Unloads all phrase commands, then reloads them from the phrases.json file
    def reload_phrases(self):
        self.remove_phrases()
        return self.init_phrases()


    ## Load phrases from json into a list of phrase objects
    def load_phrases(self, path):
        ## Insert source[key] (if it exists) into target[key], else insert a default string
        def insert_if_exists(target, source, key, default=None):
            if(key in source):
                target[key] = source[key]
            return target

        phrases = []
        with open(path) as fd:
            for phrase_raw in json.load(fd)[self.PHRASES_KEY]:
                try:
                    ## Todo: make this less ugly
                    kwargs = {}
                    help_value = phrase_raw.get(self.HELP_KEY)  # fallback for the help submenus
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.HELP_KEY)
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.BRIEF_KEY, help_value)
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.DESCRIPTION_KEY, help_value)

                    phrase_name = phrase_raw[self.NAME_KEY]
                    phrase = Phrase(
                        phrase_name,
                        phrase_raw[self.MESSAGE_KEY],
                        phrase_raw.get(self.IS_MUSIC_KEY, False),
                        **kwargs
                    )
                    phrases.append(phrase)
                    self.command_names.append(phrase_name)
                except Exception as e:
                    utilities.debug_print("Error loading {} from {}. Skipping...".format(phrase_raw, fd), e, debug_level=3)

        ## Todo: This doesn't actually result in the phrases in the help menu being sorted?
        return sorted(phrases, key=lambda phrase: phrase.name)


    ## Unloads the preset phrases from the bot's command list
    def remove_phrases(self):
        for name in self.command_names:
            self.bot.remove_command(name)
        self.command_names = []

        return True


    ## Add a phrase command to the bot's command list
    def add_phrase(self, phrase):
        if(not isinstance(phrase, Phrase)):
            raise TypeError("{} not instance of Phrase.".format(phrase))

        ## Manually build command to be added
        command = commands.Command(
            phrase.name,
            self._create_phrase_callback(phrase.message, phrase.is_music),
            **phrase.kwargs,
            **self.command_kwargs
        )
        ## _phrase_callback doesn't have an instance linked to it, 
        ## (not technically a method of Phrases?) so manually insert the correct instance anyway.
        ## This also fixes the broken category label in the help page.
        command.instance = self

        self.bot.add_command(command)


    ## Build a dynamic callback to invoke the bot's say method
    def _create_phrase_callback(self, message, is_music=False):
        ## Create a callback for speech.say
        async def _phrase_callback(self, ctx):
            ## Pass a self arg to it now that the command.instance is set to self
            speech_cog = self.speech_cog
            say = speech_cog.say.callback
            await say(speech_cog, ctx, message=message, ignore_char_limit=True)

        ## Create a callback for music.music
        async def _music_callback(self, ctx):
            music_cog = self.music_cog
            music = music_cog.music.callback
            await music(music_cog, ctx, message=message, ignore_char_limit=True)

        ## Return the appropriate callback
        if(is_music):
            return _music_callback
        else:
            return _phrase_callback


    ## Says a random phrase from the added phrases
    @commands.command(pass_context=True, no_pm=True)
    async def random(self, ctx):
        """Says a random phrase from the list of phrases."""

        random_phrase = random.choice(self.command_names)
        command = self.bot.get_command(random_phrase)
        await command.callback(self, ctx)
