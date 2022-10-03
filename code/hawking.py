import logging

import discord
from discord.ext import commands

from core import speech
from core import message_parser
from core.commands import admin
from core.commands import help_cog
from core.commands import invite_command
from core.commands import speech_config_help_command
from common import audio_player
from common import privacy_manager
from common.configuration import Configuration
from common.logging import Logging
from common.command_management import invoked_command_handler
from common.string_similarity import StringSimilarity
from common.database import dynamo_manager
from common.module.module_manager import ModuleManager
from common.ui import component_factory
from modules.phrases import phrases

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class Hawking:
    ## Initialize the bot, and add base cogs
    def __init__(self, **kwargs):
        ## Make sure there's a Discord token before doing anything else
        self.token = CONFIG_OPTIONS.get("discord_token")
        if (not self.token):
            raise RuntimeError("Unable to get Discord token!")

        ## Set the current working directory to that of the tts executable ASAP, so there's not weird issues arising
        ## from bot init and speech execution potentially being in different working directories.
        speech.TTSController.set_current_working_dir_to_tts_executable()

        self.name = CONFIG_OPTIONS.get("name", "the bot").capitalize()
        self.version = CONFIG_OPTIONS.get("version")
        self.description = CONFIG_OPTIONS.get("description", ["The retro TTS bot for Discord"])

        self.dynamo_db = dynamo_manager.DynamoManager()

        ## todo: this will eventually be removed upon the transistion to slash commands
        self.intents = discord.Intents.default();
        self.intents.message_content = True;

        ## Init the bot and module manager
        self.bot = commands.Bot(
            intents=self.intents,
            command_prefix=commands.when_mentioned,
            description='\n'.join(self.description)
        )

        ## Prepare to register modules
        self._module_manager = ModuleManager(self, self.bot)

        ## Register the modules (no circular dependencies!)
        self.module_manager.register_module(message_parser.MessageParser)
        self.module_manager.register_module(component_factory.ComponentFactory, self.bot)
        self.module_manager.register_module(admin.Admin, self, self.bot)
        self.module_manager.register_module(
            privacy_manager.PrivacyManager,
            self.bot,
            dependencies=[component_factory.ComponentFactory]
        )
        self.module_manager.register_module(
            speech_config_help_command.SpeechConfigHelpCommand,
            self.bot,
            dependencies=[component_factory.ComponentFactory]
        )
        self.module_manager.register_module(
            invite_command.InviteCommand,
            self.bot,
            dependencies=[component_factory.ComponentFactory]
        )
        self.module_manager.register_module(
            invoked_command_handler.InvokedCommandHandler,
            dependencies=[message_parser.MessageParser]
        )
        self.module_manager.register_module(audio_player.AudioPlayer, self.bot, dependencies=[admin.Admin])
        self.module_manager.register_module(
            speech.Speech,
            self.bot,
            dependencies=[invoked_command_handler.InvokedCommandHandler, message_parser.MessageParser, audio_player.AudioPlayer]
        )
        self.module_manager.register_module(
            help_cog.HelpCog,
            self.bot,
            dependencies=[component_factory.ComponentFactory, phrases.Phrases]
        )

        ## Find any dynamic modules, and prep them for loading
        self.module_manager.discover_modules()

        ## Load all of the previously registered modules!
        self.module_manager.load_registered_modules()

        ## Disable the default help command
        self.bot.help_command = None

        ## Give some feedback for when the bot is ready to go, and provide some help text via the 'playing' status
        @self.bot.event
        async def on_ready():
            loaded_help_cog = self.bot.get_cog(help_cog.HelpCog.__name__)
            if (loaded_help_cog):
                status = discord.Activity(name=f"/{loaded_help_cog.help_command.name}", type=discord.ActivityType.watching)
                await self.bot.change_presence(activity=status)

            LOGGER.info("Logged in as '{}' (version: {}), (id: {})".format(self.bot.user.name, self.version, self.bot.user.id))


        @self.bot.event
        async def on_command_error(ctx, exception):
            ## Something weird happened, log it!
            LOGGER.exception("Unhandled exception in during command execution", exception)
            self.dynamo_db.put_message_context(ctx, False)

    ## Properties

    @property
    def module_manager(self) -> ModuleManager:
        return self._module_manager

    ## Run the bot
    def run(self):
        '''Starts the bot up'''

        LOGGER.info(f"Starting up {self.name}")
        self.bot.run(self.token)


if(__name__ == "__main__"):
    Hawking().run()
