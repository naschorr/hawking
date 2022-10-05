import logging

from common.configuration import Configuration
from common.logging import Logging
from common.module.module import Module

import discord

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class ComponentFactory(Module):
    """Central module for building commonly used Discord UI components"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.name: str = CONFIG_OPTIONS.get("name", "the bot").capitalize()
        self.color: int = int(CONFIG_OPTIONS.get("accent_color_hex", "000000"), 16)
        self.repo_url = CONFIG_OPTIONS.get("repo_url")

    ## Embeds

    def create_basic_embed(self, title: str = None, description: str = None, url: str = None) -> discord.Embed:
        """Creates a basic embed with consistent coloring"""

        return discord.Embed(
            title=title,
            description=description,
            url=url,
            color=self.color
        )


    def create_embed(self, title: str = None, description: str = None, url: str = None) -> discord.Embed:
        """Creates an embed with default logo thumbnail"""

        embed = self.create_basic_embed(title, description, url)
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        return embed

    ## Buttons

    def create_repo_link_button(self) -> discord.Button:
        """Creates a button that links to the bot's repository"""

        if (self.repo_url is None):
            raise RuntimeError("No repository URL provided in configuration, unable to generate repo link button.")

        return discord.ui.Button(
            style=discord.ButtonStyle.link,
            label=f"Visit {self.name} on GitHub",
            url=self.repo_url
        )
