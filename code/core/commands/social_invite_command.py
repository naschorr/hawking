import logging

from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Cog

import discord

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class SocialInviteCommand(Cog):

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        name: str = CONFIG_OPTIONS.get("name")
        self.bot_invite_blurb: str = CONFIG_OPTIONS.get("bot_invite_blurb", CONFIG_OPTIONS.get("description")[0])
        self.bot_invite_url: str = CONFIG_OPTIONS.get("bot_invite_url")
        self.support_discord_invite_url: str = CONFIG_OPTIONS.get("support_discord_invite_url")

        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Make sure the minimum config options are populated, so a proper embed can be generated later
        if (name is not None and self.bot_invite_blurb is not None and self.bot_invite_url is not None):
            self.capitalized_name = name.capitalize()

            command = discord.app_commands.Command(
                name="social_invite",
                description=f"Posts invite links for {self.capitalized_name}, and it's official support server.",
                callback=self.social_invite_command
            )
            self.bot.tree.add_command(command)

    ## Commands

    async def social_invite_command(self, interaction: discord.Interaction):
        """Posts invite links for the bot, and its official support server."""

        # self.dynamo_db.put_message_context(ctx)

        embed = discord.Embed(
            title=self.capitalized_name,
            description=self.bot_invite_blurb,
            url=self.bot_invite_url
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        view = discord.ui.View()

        bot_invite_button = discord.ui.Button(
            style=discord.ButtonStyle.link,
            label=f"Invite {self.capitalized_name}",
            url=self.bot_invite_url
        )
        view.add_item(bot_invite_button)

        if (self.support_discord_invite_url is not None):
            support_discord_invite_button = discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Join the Support Discord",
                url=self.support_discord_invite_url
            )
            view.add_item(support_discord_invite_button)

        await interaction.response.send_message(embed=embed, view=view)
