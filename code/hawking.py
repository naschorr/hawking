## Fix inconsistent pathing between my Windows dev environment, and the Ubuntu production server.
import sys
from common import utilities

_root_path = str(utilities.get_root_path())
if _root_path not in sys.path:
    sys.path.append(_root_path)

import os
import logging
import asyncio
import argparse
from pathlib import Path
from typing import cast

import discord
from discord.ext import commands

from core.cogs import help_cog, speech_cog, speech_config_help_cog
from core.tts import tts_controller
from common import audio_player, message_parser, string_similarity
from common.cogs import admin_cog, privacy_management_cog, invite_cog
from common.configuration.configuration import HawkingConfig, load_hawking_config
from common.logging import Logging
from common.command_management import invoked_command_handler, command_reconstructor
from common.database import database_manager
from common.database.factories import anonymous_item_factory
from common.database.clients.dynamo_db import dynamo_db_client
from common.module.module_manager import ModuleManager
from common.string_similarity_config import StringSimilarityConfig
from common.ui import component_factory
from modules.phrases import phrases

DEFAULT_DESCRIPTION = "The retro TTS bot for Discord"


class Hawking:
    ## Initialize the bot, and add base cogs
    def __init__(self, config_path: Path | None = None):
        config: HawkingConfig = load_hawking_config(config_path)
        app_config = config.hawking.app
        self.logger = Logging.initialize_logging(
            logging.getLogger(self.__class__.__qualname__), config.hawking.logging
        )

        self.token = config.hawking.discord.token

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
            config.hawking.database,
            dynamo_db_client.DynamoDbClient(config.hawking.database),
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
            StringSimilarityConfig.model_validate({
                "similarity_algorithm": config.modules.phrases.similarity_algorithm,
            }),
        )
        self.module_manager.register_module(
            admin_cog.AdminCog,
            config.hawking.admin,
            self.module_manager,
            self.bot,
            dependencies=[database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            privacy_management_cog.PrivacyManagementCog,
            app_config,
            config.hawking.privacy,
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
            config.hawking.invite,
            self.bot,
            dependencies=[component_factory.ComponentFactory, database_manager.DatabaseManager],
        )
        self.module_manager.register_module(
            invoked_command_handler.InvokedCommandHandler,
            dependencies=[message_parser.MessageParser, database_manager.DatabaseManager, command_reconstructor.CommandReconstructor],
        )
        self.module_manager.register_module(
            audio_player.AudioPlayer,
            config.hawking.audio,
            self.bot,
            dependencies=[admin_cog.AdminCog, database_manager.DatabaseManager],
        )
        self.module_manager.register_module(tts_controller.TTSController, config.modules.tts)
        self.module_manager.register_module(
            speech_cog.SpeechCog,
            self.bot,
            config.modules.speech,
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
    parser = argparse.ArgumentParser(description=DEFAULT_DESCRIPTION)
    parser.add_argument(
        "--config",
        "-c",
        help="Path to the configuration directory to use",
        default=None,
        type=Path,
        action="store",
    )
    args = vars(parser.parse_args())
    Hawking(config_path=args["config"]).run()
