import importlib

import os
from collections import OrderedDict

import discord
from discord.ext import commands

import utilities
import speech
import phrases
import music
import admin

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

## Config
CONFIG_OPTIONS = utilities.load_config()


class ModuleEntry:
    def __init__(self, module, cls, *init_args, **init_kwargs):
        self.module = module
        self.cls = cls
        self.name = cls.__name__
        self.args = init_args
        self.kwargs = init_kwargs


    def get_class_callable(self):
        return getattr(self.module, self.name)


class ModuleManager:
    def __init__(self, bot):
        self.bot = bot
        self.modules = OrderedDict()


    def register(self, module, cls, *init_args, **init_kwargs):
        module_entry = ModuleEntry(module, cls, *init_args, **init_kwargs)

        self.modules[module_entry.name] = module_entry

        ## Add the module to the bot, provided it hasn't already been added.
        if(not self.bot.get_cog(module_entry.name)):
            cog_cls = module_entry.get_class_callable()
            self.bot.add_cog(cog_cls(*module_entry.args, **module_entry.kwargs))


    ## Reimport a single module
    def _reload_module(self, module):
        try:
            importlib.reload(module)
        except Exception as e:
            print("Error: ({}) reloading module: {}".format(e, module))
            return False
        else:
            return True


    ## Reload a cog attached to the bot
    def _reload_cog(self, cog_name):
        module_entry = self.modules.get(cog_name)
        assert module_entry is not None

        self.bot.remove_cog(cog_name)
        self._reload_module(module_entry.module)
        cog_cls = module_entry.get_class_callable()
        self.bot.add_cog(cog_cls(*module_entry.args, **module_entry.kwargs))


    ## Reload all of the registered modules
    def reload_all(self):
        counter = 0
        for module_name in self.modules:
            try:
                self._reload_cog(module_name)
            except Exception as e:
                print("Error: {} when reloading cog: {}".format(e, module_name))
            else:
                counter += 1

        print("Loaded {} cog{}.".format(counter, "s" if counter != 1 else ""))
        return counter


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
        ## Todo: pass kwargs to the their modules

        ## Init the bot and module manager
        self.bot = commands.Bot(
            command_prefix=commands.when_mentioned_or(self.activation_str),
            description=self.description
        )
        self.module_manager = ModuleManager(self.bot)

        ## Register the modules (Order of registration is important, make sure dependancies are loaded first)
        self.module_manager.register(speech, speech.Speech, *[self.bot])
        self.module_manager.register(phrases, phrases.Phrases,
                                     *[self, self.bot, self.phrases_file_path],
                                     **dict(pass_context=True, no_pm=True))
        self.module_manager.register(music, music.Music, *[self, self.bot])
        self.module_manager.register(admin, admin.Admin, *[self, self.bot])

        ## Give some feedback for when the bot is ready to go
        @self.bot.event
        async def on_ready():
            print("Logged in as '{}' (id:{})".format(self.bot.user.name, self.bot.user.id))

    ## Methods

    ## Add an arbitary cog to the bot
    def add_cog(self, cls):
        self.bot.add_cog(cls)


    ## Returns a cog with a given name
    def get_cog(self, cls_name):
        return self.bot.get_cog(cls_name)


    ## Returns the bot's speech cog
    def get_speech_cog(self):
        return self.bot.get_cog(speech.Speech.__name__)


    ## Returns the bot's phrases cog
    def get_phrases_cog(self):
        return self.bot.get_cog(phrases.Phrases.__name__)


    ## Run the bot
    def run(self):
        self.bot.run(utilities.load_json(self.token_file_path)[self.TOKEN_KEY])


if(__name__ == "__main__"):
    hawking = Hawking()
    # hawking.add_cog(ArbitaryClass(*args, **kwargs))
    hawking.run()