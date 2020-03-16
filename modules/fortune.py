import logging
from random import choice

import utilities

import discord
from discord.ext import commands

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class Fortune(commands.Cog):
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
        self.hawking = hawking
        self.phrases = self.FORTUNES


    @commands.command(no_pm=True, brief="Tells you your magic 8 ball fortune!")
    async def fortune(self, ctx):
        speech_cog = self.hawking.get_speech_cog()
        await speech_cog.say(ctx, choice(self.phrases), ignore_char_limit=True)


def main():
    return [Fortune, True]
