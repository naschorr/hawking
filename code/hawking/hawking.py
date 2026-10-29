## Bootstrap the code package when this file is executed directly by systemd or a shell.
import sys
from pathlib import Path

_code_path = str(Path(__file__).resolve().parents[1])
if _code_path not in sys.path:
    sys.path.insert(0, _code_path)

import os
import logging
import asyncio
from typing import cast

import discord
from discord.ext import commands

from hawking.modules.help import hawking_help_cog as help_cog
from hawking.modules.speech import speech_cog, speech_config_help_cog
from hawking.services.tts_manager import tts_controller
from hawking.core.modules.audio_player import audio_player_cog as audio_player
from hawking.core.services.message_parser import message_parser
from hawking.core.services.string_similarity import string_similarity
from hawking.core.modules.admin import admin_cog
from hawking.core.modules.privacy import privacy_cog as privacy_management_cog
from hawking.core.modules.invite import invite_cog
from hawking.configuration import HawkingConfig, load_hawking_config
from hawking.core.services.logging.logging_service import Logging
from hawking.core.services.command_management import invoked_command_handler, command_reconstructor
from hawking.core.services.database import database_manager
from hawking.core.services.database.factories import anonymous_item_factory
from hawking.core.services.database.clients.dynamo_db import dynamo_db_client
from hawking.core.services.module_manager.module_manager import ModuleManager
from hawking.core.services.string_similarity.string_similarity_config import StringSimilarityConfig
from hawking.core.ui import ui_component_factory as component_factory
from addons.phrases import phrases

class Hawking:
    ## Initialize the bot, and add base cogs
    def __init__(self, config: HawkingConfig):
        app_config = config.hawking.core.app
        self.logger = Logging.initialize_logging(
            logging.getLogger(self.__class__.__qualname__), config.hawking.core.logging
        )

        self.token = config.hawking.core.discord.token

        self.name = app_config.name.capitalize()
        self.version = app_config.version
        self.description = app_config.description

        self.bot = commands.AutoShardedBot(
            intents=discord.Intents.default(),
            command_prefix=commands.when_mentioned,
            description="\n".join(self.description),
        )

        ## Prepare to register modules
        self._module_manager = ModuleManager(config, self, self.bot)

        ## Register the modules (no circular dependencies!)
        self.module_manager.register_module(message_parser.MessageParser, dependencies=[])
        self.module_manager.register_module(
            command_reconstructor.CommandReconstructor,
            dependencies=[message_parser.MessageParser],
        )
        self.module_manager.register_module(
            anonymous_item_factory.AnonymousItemFactory,
            dependencies=[command_reconstructor.CommandReconstructor],
        )
        self.module_manager.register_module(
            database_manager.DatabaseManager,
            config.hawking.core.database,
            dynamo_db_client.DynamoDbClient(config.hawking.core.database),
            dependencies=[command_reconstructor.CommandReconstructor, anonymous_item_factory.AnonymousItemFactory],
        )
        self.module_manager.register_module(
            component_factory.ComponentFactory,
            app_config,
            self.bot,
            dependencies=[database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            string_similarity.StringSimilarity,
            config.hawking.core.string_similarity,
        )
        self.module_manager.register_module(
            admin_cog.AdminCog,
            config.hawking.core.admin,
            self.module_manager,
            self.bot,
            dependencies=[database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            privacy_management_cog.PrivacyManagementCog,
            app_config,
            config.hawking.core.privacy,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            speech_config_help_cog.SpeechConfigHelpCog,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            invite_cog.InviteCog,
            app_config,
            config.hawking.core.invite,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            invoked_command_handler.InvokedCommandHandler,
            dependencies=[message_parser.MessageParser, database_manager.DatabaseManager, command_reconstructor.CommandReconstructor],
        )
        self.module_manager.register_module(
            audio_player.AudioPlayer,
            config.hawking.core.audio,
            self.bot,
            dependencies=[admin_cog.AdminCog, database_manager.DatabaseManager],
        )
        self.module_manager.register_module(tts_controller.TTSController, config.hawking.modules.tts)
        self.module_manager.register_module(
            speech_cog.SpeechCog,
            self.bot,
            config.hawking.modules.speech,
            dependencies=[
                invoked_command_handler.InvokedCommandHandler,
                message_parser.MessageParser,
                audio_player.AudioPlayer,
                tts_controller.TTSController,
            ],
        )
        self.module_manager.register_module(
            help_cog.HelpCog,
            app_config,
            self.bot,
            dependencies=[component_factory.ComponentFactory, phrases.Phrases, database_manager.DatabaseManager],
        )

        ## Find any dynamic modules, and prep them for loading
        self.module_manager.discover_modules()

        ## Load all of the previously registered modules!
        asyncio.run(self.module_manager.load_registered_modules())

        ## Disable the default help command
        self.bot.help_command = None

        ## Set the current working directory to that of the TTS executable, otherwise the TTS interface won't
        ## necessarily work as expected
        self.tts_controller = cast(
            tts_controller.TTSController,
            self.module_manager.get_module(tts_controller.TTSController.__name__),
        )
        os.chdir(self.tts_controller.get_tts_executable_path().parent)
        self.database_manager = cast(
            database_manager.DatabaseManager,
            self.module_manager.get_module(database_manager.DatabaseManager.__name__),
        )

        @self.bot.event
        async def on_ready():
            ## Give some feedback for when the bot is ready to go, and provide some help text via the 'playing' status
            if loaded_help_cog := self.module_manager.get_module(help_cog.HelpCog.__name__):
                loaded_help_cog = cast(help_cog.HelpCog, loaded_help_cog)
                status = discord.Activity(
                    name=f"/{loaded_help_cog.help_command.name}",
                    type=discord.ActivityType.watching,
                )
                await self.bot.change_presence(activity=status)
            if self.bot.user is not None:
                self.logger.info(
                    f"Logged in as '{self.bot.user.name}' (version: {self.version}), (id: {self.bot.user.id})"
                )

        @self.bot.event
        async def on_command_error(ctx, exception):
            ## Something weird happened, log it!
            self.logger.exception("Unhandled exception in during command execution", exc_info=exception)
            await self.database_manager.store(ctx, valid=False)

    ## Properties

    @property
    def module_manager(self) -> ModuleManager:
        return self._module_manager

    ## Run the bot
    def run(self):
        """Starts the bot up."""
        self.logger.info(f"Starting up {self.name}")
        self.bot.run(self.token)


if __name__ == "__main__":
    config = load_hawking_config()
    Hawking(config).run()
