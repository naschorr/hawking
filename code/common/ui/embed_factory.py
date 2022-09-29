import logging

from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Module

import discord

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class EmbedFactory(Module):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.name: str = CONFIG_OPTIONS.get("name", "bot").capitalize()


    def create(self, title: str = None, description: str = None, url: str = None) -> discord.Embed:
        embed = discord.Embed(
            title=title or self.name,
            description=description,
            url=url
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        return embed
