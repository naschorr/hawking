import inspect
import logging

from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Cog

import discord
from discord.ext import commands

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class SpeechConfigHelpCommand(Cog):

    HAWKING_SPEECH_CONFIG_URL = 'https://github.com/naschorr/hawking/blob/master/docs/configuring_speech.md'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.dynamo_db = dynamo_manager.DynamoManager()

    ## Methods

    @commands.command(no_pm=True)
    async def speech_config(self, ctx):
        '''Posts a link to the speech documentation.'''
        
        self.dynamo_db.put_message_context(ctx)

        embed = discord.Embed(
            description='Take a look at Hawking\'s [speech configuration documentation]({}), it\'s got everything you need to get started with tweaking Hawking to do pretty much anything you\'d like.'
                .format(self.HAWKING_SPEECH_CONFIG_URL)
        )

        await ctx.send('Hey <@{}>,'.format(ctx.message.author.id), embed=embed)
