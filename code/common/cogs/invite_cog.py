import logging

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


class InviteCog(Cog):

    def __init__(self, bot: Bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

        self.bot = bot

        self.component_factory: ComponentFactory = kwargs.get('dependencies', {}).get('ComponentFactory')
        assert(self.component_factory is not None)
        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)

        self.name: str = CONFIG_OPTIONS.get("name", "the bot").capitalize()
        self.bot_invite_blurb: str = CONFIG_OPTIONS.get("bot_invite_blurb", CONFIG_OPTIONS.get("description")[0])
        self.bot_invite_url: str = CONFIG_OPTIONS.get("bot_invite_url")
        self.support_discord_invite_url: str = CONFIG_OPTIONS.get("support_discord_invite_url")

        ## Make sure the minimum config options are populated, so a proper embed can be generated later
        if (self.bot_invite_blurb is not None and self.bot_invite_url is not None):
            self.add_command(Command(
                name="invite",
                description=f"Posts invite links for {self.name}",
                callback=self.invite_command
            ))

    ## Commands

    async def invite_command(self, interaction: Interaction):

        await self.database_manager.store(interaction)

        embed = self.component_factory.create_embed(
            title=self.name,
            description=self.bot_invite_blurb,
            url=self.bot_invite_url
        )

        view = View()

        view.add_item(Button(
            style=ButtonStyle.link,
            label=f"Invite {self.name}",
            url=self.bot_invite_url
        ))

        if (self.support_discord_invite_url is not None):
            view.add_item(Button(
                style=ButtonStyle.link,
                label="Join the Support Discord",
                url=self.support_discord_invite_url
            ))

        if (repo_button := self.component_factory.create_repo_link_button()):
            view.add_item(repo_button)

        await interaction.response.send_message(embed=embed, view=view)
