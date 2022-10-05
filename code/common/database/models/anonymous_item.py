import logging
import uuid
import datetime

from common.database.models.command_item import CommandItem
from common.configuration import Configuration
from common.logging import Logging

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class AnonymousItem(CommandItem):
    def __init__(
            self,
            qualified_command_string: str,
            command_name: str,
            query: str,
            is_app_command: bool,
            created_at: datetime.datetime,
            is_valid: bool
    ):
        self.qualified_command_string = qualified_command_string
        self.command_name = command_name
        self.query = query
        self.is_app_command = is_app_command
        self.created_at = created_at
        self.is_valid = is_valid

    ## Methods

    def to_json(self) -> dict:
        return {
            "qualified_command_string": self.qualified_command_string,
            "command_name": self.command_name,
            "query": self.query,
            "is_app_command": self.is_app_command,
            "created_at": int(self.created_at.timestamp() * 1000),  # float to milliseconds timestamp
            "is_valid": self.is_valid
        }


    def build_primary_key(self) -> str:
        ## Use a UUID because we can't really guarantee that there won't be collisions with the existing data
        return str(uuid.uuid4())
