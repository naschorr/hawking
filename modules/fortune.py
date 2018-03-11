from random import choice

import discord
from discord.ext import commands


class Fortune:
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


    @commands.command(pass_context=True, no_pm=True)
    async def fortune(self, ctx):
        speech_cog = self.hawking.get_speech_cog()
        await speech_cog.say.callback(speech_cog, ctx, message=choice(self.phrases))


def main():
    return [Fortune, True]
