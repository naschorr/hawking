import logging
from random import choice

from common.logging import Logging
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer

import discord
from discord.ext import commands

## Logging
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class Fortune(DiscoverableCog):
    ## Defaults
    FORTUNES = [
        ## Positive
        "It is certain",
        "It is decidely so",
        "Without a doubt",
        "Yes definitely",
        "Without a doubt",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook good",
        "Yep",
        "Signs point to yes",
        ## Neutral
        "Reply hazy, try again",
        "Ask again later",
        "Better not tell you now",
        "Cannot predict now",
        "Concentrate and ask again",
        ## Negative
        "Don't count on it",
        "My reply is no",
        "My sources say no",
        "Outlook not so good",
        "Very doubtful"
    ]


    def __init__(self, hawking, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking
        self.speech_cog = kwargs.get('dependencies', {}).get('Speech', {})


    @commands.command(no_pm=True, brief="Tells you your magic 8 ball fortune!")
    async def fortune(self, ctx):
        await self.speech_cog._say(ctx, choice(self.FORTUNES), ignore_char_limit=True)


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(Fortune, dependencies=["Speech"])
