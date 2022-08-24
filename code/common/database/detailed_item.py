import base64
import logging
from typing import Dict
from .anonymous_item import AnonymousItem
from .command_item import CommandItem

from common import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class DetailedItem(CommandItem):
    def __init__(self, discord_context, query, command, is_valid):
        self.discord_context = discord_context
        author = self.discord_context.message.author
        channel = self.discord_context.message.channel
        guild = self.discord_context.message.guild

        self.user_id = int(author.id)
        self.user_name = "{}#{}".format(author.name, author.discriminator)
        self.timestamp = int(self.discord_context.message.created_at.timestamp() * 1000)    # float to milliseconds timestamp
        self.channel_id = channel.id
        self.channel_name = channel.name
        self.server_id = guild.id
        self.server_name = guild.name

        self.query = query
        self.command = command
        self.is_valid = is_valid
        ## Milliseconds timestamp to seconds, as AWS TTL only works in seconds increments. Defaults to a year from the timestamp
        self.expires_on = (self.timestamp / 1000) + CONFIG_OPTIONS.get("database_detailed_table_ttl_seconds", 31536000)

        self.primary_key_name = CONFIG_OPTIONS.get("boto_primary_key", "QueryId")
        self.primary_key = self.build_primary_key()

    ## Methods

    def to_json(self) -> Dict:
        return {
            'user_id': int(self.user_id),
            'user_name': str(self.user_name),
            'timestamp': int(self.timestamp),
            'channel_id': int(self.channel_id),
            'channel_name': str(self.channel_name),
            'server_id': int(self.server_id),
            'server_name': str(self.server_name),
            'query': str(self.query),
            'command': str(self.command),
            'is_valid': bool(self.is_valid),
            'expires_on': int(self.expires_on),
            self.primary_key_name: str(self.primary_key),
        }


    def build_primary_key(self) -> str:
        concatenated = "{}{}".format(self.user_id, self.timestamp)

        return base64.b64encode(bytes(concatenated, "utf-8")).decode("utf-8")
