import base64
import logging
import datetime

from discord import Member, TextChannel, VoiceChannel, Guild

from common.database.models.command_item import CommandItem
from common.configuration import Configuration
from common.logging import Logging

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class DetailedItem(CommandItem):
    def __init__(
            self,
            author: Member,
            text_channel: TextChannel,
            voice_channel: VoiceChannel | None,
            guild: Guild,
            qualified_command_string: str,
            command_name: str,
            query: str,
            is_app_command: bool,
            created_at: datetime.datetime,
            is_valid: bool
    ):
        self.user_id = int(author.id)
        self.author = author
        self.text_channel_id = text_channel.id
        self.text_channel_name = text_channel.name
        self.voice_channel_id = voice_channel.id if voice_channel else None
        self.voice_channel_name = voice_channel.name if voice_channel else None
        self.server_id = guild.id
        self.server_name = guild.name
        self.qualified_command_string = qualified_command_string
        self.command_name = command_name
        self.query = query
        self.is_app_command = is_app_command
        self.created_at = created_at
        self.is_valid = is_valid

    ## Methods

    def to_json(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_name": f"{self.author.name}#{self.author.discriminator}",
            "text_channel_id": self.text_channel_id,
            "text_channel_name": self.text_channel_name,
            "voice_channel_id": self.voice_channel_id,
            "voice_channel_name": self.voice_channel_name,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "qualified_command_string": self.qualified_command_string,
            "command_name": self.command_name,
            "query": self.query,
            "is_app_command": self.is_app_command,
            "created_at": int(self.created_at.timestamp() * 1000),  # float to milliseconds timestamp,
            "is_valid": self.is_valid
        }


    def build_primary_key(self) -> str:
        concatenated = f"{self.user_id}{self.created_at}"

        return base64.b64encode(bytes(concatenated, "utf-8")).decode("utf-8")
