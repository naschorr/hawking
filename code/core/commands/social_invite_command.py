import inspect
import logging

from common import utilities
from common.database import dynamo_manager
from common.module.module import Cog

from discord.ext import commands
from discord.ext.commands import Paginator

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class SocialInviteCommand(Cog):

    def __init__(self, hawking, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking
        self.bot = bot

        self.dynamo_db = dynamo_manager.DynamoManager()

    ## Methods

    async def send_pages(self, ctx, paginator):
        destination = ctx.channel

        for page in paginator.pages:
            await destination.send(page)

    ## Commands

    @commands.command(no_pm=True)
    async def invite(self, ctx):
        '''Posts invite links for Hawking, and its Discord server.'''

        self.dynamo_db.put_message_context(ctx)

        paginator = Paginator()
        paginator.add_line('Add Hawking to your server with this link: https://discordapp.com/oauth2/authorize?client_id=334894709292007424&scope=bot&permissions=53803072')
        paginator.close_page()
        paginator.add_line('Also, join my Discord server via: https://discord.gg/JJqx8C4')
        paginator.add_line('- Help me test unstable versions of Hawking and my other bots')
        paginator.add_line('- Let me know if something\'s broken')
        paginator.add_line('- Post suggestions for improving Hawking and my other bots')
        paginator.add_line('- Got a funny phrase you want added? Suggest it in there!')
        paginator.close_page()

        await self.send_pages(ctx, paginator)
