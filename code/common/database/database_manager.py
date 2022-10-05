import logging
import inspect

from discord import app_commands, Interaction
from discord.ext.commands import Context

from common.configuration import Configuration
from common.logging import Logging
from common.command_management.command_reconstructor import CommandReconstructor
from common.database.factories.anonymous_item_factory import AnonymousItemFactory
from common.database.models.anonymous_item import AnonymousItem
from common.database.models.detailed_item import DetailedItem
from common.database.database_client import DatabaseClient
from common.exceptions import UnableToStoreInDatabaseException
from common.module.module import Module

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class DatabaseManager(Module):
    def __init__(self, client: DatabaseClient = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.command_reconstructor: CommandReconstructor = kwargs.get('dependencies', {}).get('CommandReconstructor')
        assert (self.command_reconstructor is not None)
        self.anonymous_item_factory: AnonymousItemFactory = kwargs.get('dependencies', {}).get('AnonymousItemFactory')
        assert (self.anonymous_item_factory is not None)

        self.enabled = CONFIG_OPTIONS.get('database_enable', False)

        self._client: DatabaseClient = client

    ## Methods

    def register_client(self, client: DatabaseClient):
        LOGGER.info(f"Registering new database client: {client.name}")
        self._client = client


    def _build_detailed_item_from_context(self, context: Context, valid: bool = None) -> DetailedItem:
        """Builds a DetailedItem from the given discord.Context, pulled from the message that invoked the bot"""

        voice_state = context.author.voice
        voice_channel = None
        if (voice_state):
            voice_channel = voice_state.channel

        return DetailedItem(
            context.author,
            context.channel,
            voice_channel,
            context.guild,
            context.command.qualified_name,
            context.command.name,
            self.command_reconstructor.reconstruct_command_string(context, add_parameter_keys = True),
            isinstance(context.command, app_commands.Command),
            context.message.created_at,
            valid or not context.command_failed
        )


    def _build_detailed_item_from_interaction(self, interaction: Interaction, valid: bool = None) -> DetailedItem:
        """Builds a DetailedItem from the given discord.Interaction, pulled from the message that invoked the bot"""

        voice_state = interaction.user.voice
        voice_channel = None
        if (voice_state):
            voice_channel = voice_state.channel

        return DetailedItem(
            interaction.user,
            interaction.channel,
            voice_channel,
            interaction.guild,
            interaction.command.qualified_name,
            interaction.command.name,
            self.command_reconstructor.reconstruct_command_string(interaction, add_parameter_keys = True),
            isinstance(interaction.command, app_commands.Command),
            interaction.created_at,
            valid or not interaction.command_failed
        )


    async def _store(self, detailed_item: DetailedItem, anonymous_item: AnonymousItem):
        """Handles storage of the given DetailedItem in the registered database"""

        if (not self.enabled):
            return

        if (self._client is None):
            raise UnableToStoreInDatabaseException("Unable to store data without a client registered!")

        await self._client.store(detailed_item, anonymous_item)


    async def store(self, data: Context | Interaction, valid: bool = None):
        """Handles storage of the given Context or Interaction (by converting it into a DetailedItem) in the registered database"""

        if (isinstance(data, Context)):
            detailed_item = self._build_detailed_item_from_context(data, valid)
            anonymous_item = self.anonymous_item_factory.create(data, detailed_item)
        elif (isinstance(data, Interaction)):
            detailed_item = self._build_detailed_item_from_interaction(data, valid)
            anonymous_item = self.anonymous_item_factory.create(data, detailed_item)
        else:
            raise UnableToStoreInDatabaseException("Data is not of type Context or Interaction")

        await self._store(detailed_item, anonymous_item)


    async def batch_delete_users(self, user_ids: list[str]):
        """Handles a batched delete operation to remove users from from the Detailed table"""

        if (not self.enabled):
            return

        if (self._client is None):
            raise UnableToStoreInDatabaseException("Unable to batch delete data without a client registered!")

        await self._client.batch_delete_users(user_ids)
