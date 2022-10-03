import logging
import uuid
from typing import Dict
from .command_item import CommandItem

from common.configuration import Configuration
from common.logging import Logging

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class AnonymousItem(CommandItem):
    def __init__(self, discord_context, command, query, is_valid):
        self.timestamp = int(discord_context.message.created_at.timestamp() * 1000)
        self.command = command
        self.query = query
        self.is_valid = is_valid

        self.primary_key_name = CONFIG_OPTIONS.get("boto_primary_key", "QueryId")
        self.primary_key = self.build_primary_key()

    ## Methods

    def to_json(self) -> Dict:
        return {
            'timestamp': int(self.timestamp),
            'command': str(self.command),
            'query': str(self.query),
            'is_valid': str(self.is_valid),
            self.primary_key_name: str(self.primary_key),
        }


    def build_primary_key(self) -> str:
        ## Use a UUID because we can't really guarantee that there won't be collisions with the existing data
        return str(uuid.uuid4())
