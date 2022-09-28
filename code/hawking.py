import inspect
import os
import time
import logging
from concurrent.futures import TimeoutError
from collections import OrderedDict

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands.errors import CommandInvokeError

from core import speech
from core import message_parser
from core.commands import admin
from core.commands import help_command
from core.commands import social_invite_command
from core.commands import speech_config_help_command
from common import audio_player
from common import privacy_manager
from common.configuration import Configuration
from common.logging import Logging
from common.command_management import invoked_command_handler
from common.string_similarity import StringSimilarity
from common.database import dynamo_manager
from common.module.module_manager import ModuleManager

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


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
    INVALID_COMMAND_MINIMUM_SIMILARITY = "invalid_command_minimum_similarity"

    ## Defaults
    VERSION = CONFIG_OPTIONS.get(VERSION_KEY, "Invalid version")
    ACTIVATION_STR = CONFIG_OPTIONS.get(ACTIVATION_STR_KEY, "\\")


    ## Initialize the bot, and add base cogs
    def __init__(self, **kwargs):
        ## Make sure there's a Discord token before doing anything else
        self.token = CONFIG_OPTIONS.get("discord_token")
        if (not self.token):
            raise RuntimeError("Unable to get Discord token!")

        ## todo: this will eventually be removed upon the transistion to slash commands
        self.intents = discord.Intents.default();
        self.intents.message_content = True;

        ## Set the current working directory to that of the tts executable ASAP, so there's not weird issues arising
        ## from bot init and speech execution potentially being in different working directories.
        speech.TTSController.set_current_working_dir_to_tts_executable()

        self.version = kwargs.get(self.VERSION_KEY, self.VERSION)
        self.activation_str = kwargs.get(self.ACTIVATION_STR_KEY, self.ACTIVATION_STR)
        self.description = kwargs.get("description", ["The retro TTS bot for Discord"])
        self.invalid_command_minimum_similarity = float(kwargs.get(self.INVALID_COMMAND_MINIMUM_SIMILARITY, 0.66))

        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Init the bot and module manager
        self.bot = commands.Bot(
            intents=self.intents,
            command_prefix=commands.when_mentioned_or(self.activation_str),
            description='\n'.join(self.description)
        )

        ## Apply customized HelpCommand
        self.bot.help_command = help_command.HawkingHelpCommand()

        ## Prepare to register modules
        self._module_manager = ModuleManager(self, self.bot)

        ## Register the modules (no circular dependencies!)
        self.module_manager.register_module(admin.Admin, self, self.bot)
        self.module_manager.register_module(privacy_manager.PrivacyManager, self.bot, name='Hawking')
        self.module_manager.register_module(speech_config_help_command.SpeechConfigHelpCommand, self.bot)
        self.module_manager.register_module(social_invite_command.SocialInviteCommand, self.bot)
        self.module_manager.register_module(invoked_command_handler.InvokedCommandHandler)
        self.module_manager.register_module(message_parser.MessageParser)
        self.module_manager.register_module(audio_player.AudioPlayer, self.bot, dependencies=[admin.Admin])
        self.module_manager.register_module(
            speech.Speech,
            self.bot,
            dependencies=[invoked_command_handler.InvokedCommandHandler, message_parser.MessageParser, audio_player.AudioPlayer]
        )

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

            LOGGER.info("Logged in as '{}' (version: {}), (id: {})".format(self.bot.user.name, self.version, self.bot.user.id))


        ## Give some feedback to users when their command doesn't execute.
        @self.bot.event
        async def on_command_error(ctx, exception):
            '''Handles command errors. Attempts to find a similar command and suggests it, otherwise directs the user to the help prompt.'''

            ## todo: reevaluate the necessity of this as the bot migrates to slash commands. Cogs can likely handle
            ##       errors on their own with the `cog_command_error` overridden method as well.

            self.dynamo_db.put_message_context(ctx, False)

            ## Attempt to find a command that's similar to the one they wanted. Otherwise just direct them to the help page
            most_similar_command = self.find_most_similar_command(ctx.message.content)

            if (most_similar_command[0] == ctx.invoked_with):
                LOGGER.exception("Unable to complete command, with content: {}, for author: {}, in channel {}, in server: {}".format(
                    ctx.message.content,
                    ctx.message.author.name,
                    ctx.message.channel.name,
                    ctx.guild.name
                ), exc_info=exception)
                ## Handle issues where the command is valid, but couldn't be completed for whatever reason.
                await ctx.send("I'm sorry <@{}>, I'm afraid I can't do that.\nSomething went wrong, and I couldn't complete the command.".format(ctx.message.author.id))
            else:
                LOGGER.exception("Received invalid command: '{0}{1}', suggested: '{0}{2}', for author: {3}, in server: {4}".format(
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

    ## Properties

    @property
    def module_manager(self) -> ModuleManager:
        return self._module_manager

    ## Methods

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

        LOGGER.info('Starting up the bot.')
        self.bot.run(self.token)


if(__name__ == "__main__"):
    Hawking().run()
