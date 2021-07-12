import inspect
import logging

from common import utilities
from common import dynamo_manager
from common.module.discoverable_module import DiscoverableCog

import discord
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class SpeechConfigHelpCommand(DiscoverableCog):

    HAWKING_SPEECH_CONFIG_URL = 'https://github.com/naschorr/hawking/blob/master/docs/configuring_speech.md'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.dynamo_db = dynamo_manager.DynamoManager()

        # self.help_command = self.bot.get_command('help')
        # if (not self.help_command):
        #     raise RuntimeError('Unable to locate default help command')
        
        self.build_add_speech_config_help_command()

    ## Methods

    def build_add_speech_config_help_command(self):
        '''
        The `\help speech_config` command must be parented to the main HawkingHelpCommand, so it'll properly render in
        the list of help commands. However, setting `parent=self.help_command` won't work as decorators don't have
        access to `self`. This means we've gotta build the Command manually.
        '''

        speech_config_help_command = commands.Command(
            self.speech_config,
            name='speech_config',
            no_pm=True,
            help='Posts a link to the Hawking speech configuration documentation.'
        )
        self.bot.add_command(speech_config_help_command)


    async def speech_config(self, ctx):
        '''Posts a link to the speech documentation.'''
        
        self.dynamo_db.put(dynamo_manager.CommandItem(
            ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))

        embed = discord.Embed(
            description='Take a look at Hawking\'s [speech configuration documentation]({}), it\'s got everything you need to get started with tweaking Hawking to do pretty much anything you\'d like.'
                .format(self.HAWKING_SPEECH_CONFIG_URL)
        )

        await ctx.send('Hey <@{}>,'.format(ctx.message.author.id), embed=embed)
