import logging

from common.configuration import Configuration
from common.database.database_manager import DatabaseManager
from common.logging import Logging
from common.module.module import Cog
from common.ui.component_factory import ComponentFactory

import discord

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class SpeechConfigHelpCommand(Cog):

    HAWKING_SPEECH_CONFIG_URL = "https://github.com/naschorr/hawking/blob/master/docs/configuring_speech.md"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.component_factory: ComponentFactory = kwargs.get('dependencies', {}).get('ComponentFactory')
        assert(self.component_factory is not None)
        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)

    ## Methods

    @discord.app_commands.command(name="speech_config")
    async def speech_config_command(self, interaction: discord.Interaction):
        """Posts a link to the speech config docs"""

        await self.database_manager.store(interaction)

        description = (
            f"Take a look at Hawking's [speech configuration documentation]({self.HAWKING_SPEECH_CONFIG_URL}). It's "
            "got everything you need to get started with tweaking Hawking to do pretty much anything you'd like!"
        )

        embed = self.component_factory.create_embed(
            title="Speech Configuration",
            description=description,
            url=self.HAWKING_SPEECH_CONFIG_URL
        )

        view = discord.ui.View()

        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Read the Speech Config docs",
            url=self.HAWKING_SPEECH_CONFIG_URL
        ))

        if (repo_button := self.component_factory.create_repo_link_button()):
            view.add_item(repo_button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
