import logging

from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Cog
from common.ui.component_factory import ComponentFactory

import discord

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class InviteCommand(Cog):

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.component_factory: ComponentFactory = kwargs.get('dependencies', {}).get('ComponentFactory')
        assert(self.component_factory is not None)

        name: str = CONFIG_OPTIONS.get("name")
        self.bot_invite_blurb: str = CONFIG_OPTIONS.get("bot_invite_blurb", CONFIG_OPTIONS.get("description")[0])
        self.bot_invite_url: str = CONFIG_OPTIONS.get("bot_invite_url")
        self.support_discord_invite_url: str = CONFIG_OPTIONS.get("support_discord_invite_url")

        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Make sure the minimum config options are populated, so a proper embed can be generated later
        if (name is not None and self.bot_invite_blurb is not None and self.bot_invite_url is not None):
            self.capitalized_name = name.capitalize()

            command = discord.app_commands.Command(
                name="invite",
                description=f"Posts invite links for {self.capitalized_name}",
                callback=self.invite_command
            )
            self.bot.tree.add_command(command)

    ## Commands

    async def invite_command(self, interaction: discord.Interaction):

        # self.dynamo_db.put_message_context(ctx)

        embed = self.component_factory.create_embed(
            title=self.capitalized_name,
            description=self.bot_invite_blurb,
            url=self.bot_invite_url
        )

        view = discord.ui.View()

        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label=f"Invite {self.capitalized_name}",
            url=self.bot_invite_url
        ))

        if (self.support_discord_invite_url is not None):
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Join the Support Discord",
                url=self.support_discord_invite_url
            ))

        if (repo_button := self.component_factory.create_repo_link_button()):
            view.add_item(repo_button)

        await interaction.response.send_message(embed=embed, view=view)
