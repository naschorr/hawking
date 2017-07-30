import os

import discord
from discord.ext import commands

import utilities
import speech
import phrases
import music
from admin import Admin

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

## Config
CONFIG_OPTIONS = utilities.load_config()


class Hawking:
    ## Keys and Defaults
    ## Basically, any given class can be configured by changing the respective value for the
    ## desired key in config.json (see the Keys section at the top of each class for a list of
    ## keys). However, if you want to use Hawking as a part of something else, you may want to
    ## dynamically configure objects as necessary. Thus, you can also instantiate classes with
    ## keyworded arguments, which will then override any existing defaults, or config.json data.
    ## The existing defaults in each class are sort of like a fallback, in case the config.json is
    ## broken in some way.

    ## Keys
    ACTIVATION_STR_KEY = "activation_str"
    DESCRIPTION_KEY = "description"
    TOKEN_KEY = "token"
    TOKEN_FILE_KEY = "token_file"
    TOKEN_FILE_PATH_KEY = "token_file_path"
    PHRASES_FILE_KEY = "phrases_file"
    PHRASES_FILE_PATH_KEY = "phrases_file_path"

    ## Defaults
    ACTIVATION_STR = CONFIG_OPTIONS.get(ACTIVATION_STR_KEY, "\\")
    DESCRIPTION = CONFIG_OPTIONS.get(DESCRIPTION_KEY, "A retro TTS bot for Discord (Alpha)\n Visit https://github.com/naschorr/hawking")
    TOKEN_FILE = CONFIG_OPTIONS.get(TOKEN_FILE_KEY, "token.json")
    TOKEN_FILE_PATH = CONFIG_OPTIONS.get(TOKEN_FILE_PATH_KEY, os.sep.join([utilities.get_root_path(), TOKEN_FILE]))
    PHRASES_FILE = CONFIG_OPTIONS.get(PHRASES_FILE_KEY, "phrases.json")
    PHRASES_FILE_PATH = CONFIG_OPTIONS.get(PHRASES_FILE_PATH_KEY, os.sep.join([utilities.get_root_path(), PHRASES_FILE]))


    ## Initialize the bot, and add base cogs
    def __init__(self, **kwargs):
        ## Todo: allow for arbitary module cogs

        self.activation_str = kwargs.get(self.ACTIVATION_STR_KEY, self.ACTIVATION_STR)
        self.description = kwargs.get(self.DESCRIPTION_KEY, self.DESCRIPTION)
        self.token_file_path = kwargs.get(self.TOKEN_FILE_PATH_KEY, self.TOKEN_FILE_PATH)
        self.phrases_file_path = kwargs.get(self.PHRASES_FILE_PATH_KEY, self.PHRASES_FILE_PATH)

        ## Init the bot
        self.bot = commands.Bot(
            command_prefix=commands.when_mentioned_or(self.activation_str),
            description=self.description
        )

        ## Init and add admin cog
        admin = Admin(self.bot)
        self.add_cog(admin)

        ## Prepare modules for registration
        speech_module = speech
        speech_cls = speech.Speech
        speech_name = "Speech"
        speech_args = [self.bot]

        phrases_module = phrases
        phrases_cls = phrases.Phrases
        phrases_name = "Phrases"
        phrases_args = [self.bot, self.phrases_file_path]
        phrases_kwargs = dict(pass_context=True, no_pm=True)

        music_module = music
        music_cls = music.Music
        music_name = "Music"
        music_args = [self.bot]

        ## Register the modules (Order of registration is important, make sure dependancies are loaded first)
        admin.register_module(speech_module, speech_cls, speech_name, *speech_args)
        admin.register_module(phrases_module, phrases_cls, phrases_name, *phrases_args, **phrases_kwargs)
        admin.register_module(music_module, music_cls, music_name, *music_args)

        @self.bot.event
        async def on_ready():
            print("Logged in as '{}' (id:{})".format(self.bot.user.name, self.bot.user.id))

    ## Methods

    ## Add an arbitary cog to the bot
    def add_cog(self, cls):
        self.bot.add_cog(cls)


    ## Run the bot
    def run(self):
        self.bot.run(utilities.load_json(self.token_file_path)[self.TOKEN_KEY])


if(__name__ == "__main__"):
    hawking = Hawking()
    # hawking.add_cog(ArbitaryClass(*args, **kwargs))
    hawking.run()