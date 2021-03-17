import inspect
import os
import time
import logging
from concurrent.futures import TimeoutError
from collections import OrderedDict

import discord
from discord.ext import commands
from discord.ext.commands.errors import CommandInvokeError

import utilities
import privacy_manager
import social_helper
import audio_player
import speech
import admin
import message_parser
import help_command
import dynamo_manager
from string_similarity import StringSimilarity
from module_manager import ModuleEntry, ModuleManager

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


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
    VERSION_KEY = "version"
    ACTIVATION_STR_KEY = "activation_str"
    DESCRIPTION_KEY = "description"
    INVALID_COMMAND_MINIMUM_SIMILARITY = "invalid_command_minimum_similarity"

    ## Defaults
    VERSION = CONFIG_OPTIONS.get(VERSION_KEY, "Invalid version")
    ACTIVATION_STR = CONFIG_OPTIONS.get(ACTIVATION_STR_KEY, "\\")
    DESCRIPTION = CONFIG_OPTIONS.get(DESCRIPTION_KEY, "A retro TTS bot for Discord\n Visit https://github.com/naschorr/hawking")


    ## Initialize the bot, and add base cogs
    def __init__(self, **kwargs):
        ## Make sure there's a Discord token before doing anything else
        self.token = CONFIG_OPTIONS.get("discord_token")
        if (not self.token):
            raise RuntimeError("Unable to get Discord token!")

        self.version = kwargs.get(self.VERSION_KEY, self.VERSION)
        self.activation_str = kwargs.get(self.ACTIVATION_STR_KEY, self.ACTIVATION_STR)
        self.description = kwargs.get(self.DESCRIPTION_KEY, self.DESCRIPTION)
        self.invalid_command_minimum_similarity = float(kwargs.get(self.INVALID_COMMAND_MINIMUM_SIMILARITY, 0.66))

        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Init the bot and module manager
        self.bot = commands.Bot(
            command_prefix=commands.when_mentioned_or(self.activation_str),
            description='\n'.join(self.description)
        )
        self.module_manager = ModuleManager(self, self.bot)

        ## Apply customized HelpCommand
        self.bot.help_command = help_command.HawkingHelpCommand()

        ## Register the modules
        self.module_manager.register_module(privacy_manager.PrivacyManager, True, self, self.bot)
        self.module_manager.register_module(social_helper.SocialHelper, True, self, self.bot)
        self.module_manager.register_module(message_parser.MessageParser, False)
        self.module_manager.register_module(admin.Admin, True, self, self.bot)
        self.module_manager.register_module(speech.Speech, True, self, dependencies = [message_parser.MessageParser.__name__])
        self.module_manager.register_module(audio_player.AudioPlayer, True, self.bot, lambda _: self.get_speech_cog().play_random_channel_timeout_message, dependencies = [speech.Speech.__name__])

        ## Find any dynamic modules, and prep them for loading
        self.module_manager.discover_modules()

        ## Load all of the previously registered modules!
        self.module_manager.load_registered_modules()

        ## Give some feedback for when the bot is ready to go, and provide some help text via the 'playing' status
        @self.bot.event
        async def on_ready():
            ## todo: Activity instead of Game? Potentially remove "Playing" text below bot
            bot_status = discord.Game(type=0, name="Use {}help".format(self.activation_str))
            await self.bot.change_presence(activity=bot_status)

            logger.info("Logged in as '{}' (version: {}), (id: {})".format(self.bot.user.name, self.version, self.bot.user.id))


        ## Give some feedback to users when their command doesn't execute.
        @self.bot.event
        async def on_command_error(ctx, exception):
            '''Handles command errors. Attempts to find a similar command and suggests it, otherwise directs the user to the help prompt.'''

            self.dynamo_db.put(dynamo_manager.CommandItem(
                ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False, str(exception)))

            ## Attempt to find a command that's similar to the one they wanted. Otherwise just direct them to the help page
            most_similar_command = self.find_most_similar_command(ctx.message.content)

            if (most_similar_command[0] == ctx.invoked_with):
                logger.exception("Unable to complete command, with content: {}, for author: {}, in channel {}, in server: {}".format(
                    ctx.message.content,
                    ctx.message.author.name,
                    ctx.guild.name
                ), exc_info=exception)
                ## Handle issues where the command is valid, but couldn't be completed for whatever reason.
                await ctx.send("I'm sorry <@{}>, I'm afraid I can't do that.\nSomething went wrong, and I couldn't complete the command.".format(ctx.message.author.id))
            else:
                logger.exception("Received invalid command: '{0}{1}', suggested: '{0}{2}', for author: {3}, in server: {4}".format(
                    self.activation_str,
                    ctx.invoked_with,
                    most_similar_command[0],
                    ctx.message.author.name,
                    ctx.guild.name
                ), exc_info=exception)

                help_text_chunks = [
                    "Sorry <@{}>, **{}{}** isn't a valid command.".format(ctx.message.author.id, ctx.prefix, ctx.invoked_with)
                ]

                if (most_similar_command[1] > self.invalid_command_minimum_similarity):
                    help_text_chunks.append("Did you mean **{}{}**?".format(self.activation_str, most_similar_command[0]))
                else:
                    help_text_chunks.append("Try the **{}help** page.".format(self.activation_str))

                ## Dump output to user
                await ctx.send(" ".join(help_text_chunks))
                return

    ## Methods

    ## Add an arbitary cog to the bot
    def add_cog(self, cls):
        self.bot.add_cog(cls)


    ## Returns a cog with a given name
    def get_cog(self, cls_name):
        return self.bot.get_cog(cls_name)


    ## Returns the bot's audio player cog
    def get_audio_player_cog(self):
        return self.bot.get_cog("AudioPlayer")


    ## Returns the bot's audio player cog
    def get_speech_cog(self):
        return self.bot.get_cog("Speech")


    ## Returns the bot's phrases cog
    def get_phrases_cog(self):
        return self.bot.get_cog("Phrases")


    ## Returns the bot's music cog
    def get_music_cog(self):
        return self.bot.get_cog("Music")


    ## Finds the most similar command to the supplied one
    def find_most_similar_command(self, command):
        ## Build a message string that we can compare with.
        try:
            message = command[len(self.activation_str):]
        except TypeError:
            message = command

        ## Get a list of all visible commands 
        commands = [cmd.name for cmd in self.bot.commands if not cmd.hidden]

        ## Find the most similar command
        most_similar_command = (None, 0)
        for key in commands:
            distance = StringSimilarity.similarity(key, message)
            if (distance > most_similar_command[1]):
                most_similar_command = (key, distance)

        return most_similar_command


    ## Run the bot
    def run(self):
        '''Starts the bot up'''

        ## So ideally there would be some flavor of atexit.register or signal.signal command to gracefully shut the bot
        ## down upon SIGTERM or SIGINT. However that doesn't seem to be possible at the moment. Discord.py's got most of
        ## the functionality built into the base close() method that fires on SIGINT and SIGTERM, but the bot never ends
        ## up getting properly disconnected from the voice channels that it's connected to. I end up having to wait for
        ## a time out. Otherwise the bot will be in a weird state upon starting back up, and attempting to speak in one
        ## of the channels that it was previously in. Fortunately this bad state will self-recover in a minute or so,
        ## but it's still unpleasant. A temporary fix is to bump up the RestartSec= property in the service config to be
        ## long enough to allow for the bot to be forcefully disconnected

        logger.info('Starting up the bot.')
        self.bot.run(self.token)


if(__name__ == "__main__"):
    Hawking().run()
