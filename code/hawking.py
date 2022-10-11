## Fix inconsistent pathing between my Windows dev environment, and the Ubuntu production server. This needs to happen
## before the imports so they know where to search.
import sys
from common import utilities
_root_path = str(utilities.get_root_path())
if (_root_path not in sys.path):
    sys.path.append(_root_path)

## Importing as usual now
import logging
import asyncio

import discord
from discord.ext import commands

from core import speech, message_parser
from core.cogs import admin_cog, help_cog, speech_config_help_cog
from common import audio_player
from common.cogs import privacy_management_cog, invite_cog
from common.configuration import Configuration
from common.logging import Logging
from common.command_management import invoked_command_handler, command_reconstructor
from common.database import database_manager
from common.database.factories import anonymous_item_factory
from common.database.clients.dynamo_db import dynamo_db_client
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

        ## Init the bot and module manager
        self.bot = commands.Bot(
            intents=discord.Intents.default(),
            command_prefix=commands.when_mentioned,
            description='\n'.join(self.description)
        )

        ## Prepare to register modules
        self._module_manager = ModuleManager(self, self.bot)

        ## Register the modules (no circular dependencies!)
        self.module_manager.register_module(message_parser.MessageParser)
        self.module_manager.register_module(
            command_reconstructor.CommandReconstructor,
            dependencies=[message_parser.MessageParser]
        )
        self.module_manager.register_module(
            anonymous_item_factory.AnonymousItemFactory,
            dependencies=[command_reconstructor.CommandReconstructor]
        )
        self.module_manager.register_module(
            database_manager.DatabaseManager,
            dynamo_db_client.DynamoDbClient(),
            dependencies=[command_reconstructor.CommandReconstructor, anonymous_item_factory.AnonymousItemFactory]
        )
        self.module_manager.register_module(
            component_factory.ComponentFactory,
            self.bot,
            dependencies=[database_manager.DatabaseManager]
        )
        self.module_manager.register_module(
            admin_cog.AdminCog,
            self,
            self.bot,
            dependencies=[database_manager.DatabaseManager]
        )
        self.module_manager.register_module(
            privacy_management_cog.PrivacyManagementCog,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager]
        )
        self.module_manager.register_module(
            speech_config_help_cog.SpeechConfigHelpCog,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager]
        )
        self.module_manager.register_module(
            invite_cog.InviteCog,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager]
        )
        self.module_manager.register_module(
            invoked_command_handler.InvokedCommandHandler,
            dependencies=[message_parser.MessageParser, database_manager.DatabaseManager, command_reconstructor.CommandReconstructor]
        )
        self.module_manager.register_module(
            audio_player.AudioPlayer,
            self.bot,
            dependencies=[admin_cog.AdminCog, database_manager.DatabaseManager]
        )
        self.module_manager.register_module(
            speech.Speech,
            self.bot,
            dependencies=[invoked_command_handler.InvokedCommandHandler, message_parser.MessageParser, audio_player.AudioPlayer]
        )
        self.module_manager.register_module(
            help_cog.HelpCog,
            self.bot,
            dependencies=[component_factory.ComponentFactory, phrases.Phrases, database_manager.DatabaseManager]
        )

        ## Find any dynamic modules, and prep them for loading
        self.module_manager.discover_modules()

        ## Load all of the previously registered modules!
        asyncio.run(self.module_manager.load_registered_modules())

        ## Disable the default help command
        self.bot.help_command = None

        ## Get a reference to the database manager for on_command_error storage
        self.database_manager: database_manager.DatabaseManager = self.module_manager.get_module(database_manager.DatabaseManager.__name__)

        ## Give some feedback for when the bot is ready to go, and provide some help text via the 'playing' status
        @self.bot.event
        async def on_ready():
            if (loaded_help_cog := self.module_manager.get_module(help_cog.HelpCog.__name__)):
                status = discord.Activity(name=f"/{loaded_help_cog.help_command.name}", type=discord.ActivityType.watching)
                await self.bot.change_presence(activity=status)

            LOGGER.info("Logged in as '{}' (version: {}), (id: {})".format(self.bot.user.name, self.version, self.bot.user.id))


        @self.bot.event
        async def on_command_error(ctx, exception):
            ## Something weird happened, log it!
            LOGGER.exception("Unhandled exception in during command execution", exception)
            await self.database_manager.store(ctx, valid=False)

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
