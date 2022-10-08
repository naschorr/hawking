import logging
from subprocess import call

from common.configuration import Configuration
from common.database.database_manager import DatabaseManager
from common.logging import Logging
from common.module.module import Cog
from common.ui.component_factory import ComponentFactory

from discord import Interaction, ButtonStyle
from discord.app_commands import Command
from discord.ext.commands import Bot
from discord.ui import View, Button

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class SpeechConfigHelpCommand(Cog):

    HAWKING_SPEECH_CONFIG_URL = "https://github.com/naschorr/hawking/blob/master/docs/configuring_speech.md"

    def __init__(self, bot: Bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

        self.bot = bot

        self.component_factory: ComponentFactory = kwargs.get('dependencies', {}).get('ComponentFactory')
        assert(self.component_factory is not None)
        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)

        self.add_command(Command(
            name="speech_config",
            description=self.speech_config_command.__doc__,
            callback=self.speech_config_command
        ))

    ## Methods

    async def speech_config_command(self, interaction: Interaction):
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

        view = View()

        view.add_item(Button(
            style=ButtonStyle.link,
            label="Read the Speech Config docs",
            url=self.HAWKING_SPEECH_CONFIG_URL
        ))

        if (repo_button := self.component_factory.create_repo_link_button()):
            view.add_item(repo_button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
