import logging

from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Cog

import discord

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class SpeechConfigHelpCommand(Cog):

    HAWKING_SPEECH_CONFIG_URL = "https://github.com/naschorr/hawking/blob/master/docs/configuring_speech.md"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.repo_url = CONFIG_OPTIONS.get("bot_repo_url")
        self.dynamo_db = dynamo_manager.DynamoManager()

    ## Methods

    @discord.app_commands.command(name="speech_config")
    async def speech_config_command(self, interaction: discord.Interaction):
        """Posts a link to the speech configuration documentation."""

        # self.dynamo_db.put_message_context(ctx)

        description = (
            f"Take a look at Hawking's [speech configuration documentation]({self.HAWKING_SPEECH_CONFIG_URL}). It's "
            "got everything you need to get started with tweaking Hawking to do pretty much anything you'd like!"
        )

        embed = discord.Embed(
            title="Hawking Speech Configuration",
            description=description,
            url=self.HAWKING_SPEECH_CONFIG_URL
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        view = discord.ui.View()

        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Read the Speech Config docs",
            url=self.HAWKING_SPEECH_CONFIG_URL
        ))

        if (self.repo_url is not None):
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Visit Hawking on GitHub",
                url=self.repo_url
            ))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
