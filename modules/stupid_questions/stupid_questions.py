import os
import logging
import random
import time
from pathlib import Path

from common import utilities
from common.exceptions import ModuleLoadException
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer
from question import Question

import discord
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_module_config(Path(__file__).parent)

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class StupidQuestions(DiscoverableCog):
    THOUGHT_PROVOKING_STRINGS = [
        "🤔?",
        "have you ever pondered:",
        "what do you think about this:",
        "have you ever considered:",
        "do you ever wonder about this:",
        "have a nice long think about this one:",
        "what do you think scholars in a thousand years will think about this:",
        "do you ever wonder why we're here? No? Ok, well have a wonder about this:",
        "take a gander at this highly intelligent and deeply insightful question:",
        "it's now time for us to plant some daffodils of opinion on the roundabout of chat at the end of conversation street, and discuss:"
    ]

    def __init__(self, hawking, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking
        self.bot = bot

        ## Handle Reddit dependency
        reddit_dependency = kwargs.get('dependencies', {}).get('Reddit', {})
        self.reddit = reddit_dependency.reddit
        if (not reddit_dependency.successful):
            self.successful = False
            return

        self.questions = []
        self.is_mid_question_refresh = False
        self.last_question_refresh_time = time.time()

        ## Load config data
        self.submission_top_time = CONFIG_OPTIONS.get("stupid_question_top_time", "month")
        self.submission_count = CONFIG_OPTIONS.get("stupid_question_submission_count", 500)
        self.refresh_time_seconds = CONFIG_OPTIONS.get("stupid_question_refresh_time_seconds", 21600)
        subreddits = CONFIG_OPTIONS.get("stupid_question_subreddits", ["NoStupidQuestions"])

        try:
            ## Use a multireddit to pull random post from any of the chosen subreddits
            self.subreddit = self.reddit.subreddit("+".join(subreddits))
        except Exception as e:
            raise ModuleLoadException("Unable to create reddit/subreddit instance", e)

        self.bot.loop.create_task(self.load_questions())
    
        self.successful = True


    async def load_questions(self) -> None:
        ## Don't try to pull more data from Reddit if it's already happening
        if (self.is_mid_question_refresh):
            logger.debug("Skipping load_questions as they're already being refreshed.")
            return
        self.is_mid_question_refresh = True

        logger.info("Loading questions from reddit: top({}), {} submissions".format(
            self.submission_top_time,
            self.submission_count
        ))

        questions = []
        try:
            submission_generator = self.subreddit.top(self.submission_top_time, limit=self.submission_count)
        except Exception:
            logger.exception("Unable to load submission from Reddit.")
            return

        for submission in submission_generator:
            questions.append(Question(submission.title, submission.subreddit.display_name, submission.shortlink))

        self.last_question_refresh_time = time.time()
        self.questions = questions
        self.is_mid_question_refresh = False

        logger.info("{} questions loaded at {}".format(len(self.questions), time.asctime()))


    def get_question(self) -> str:
        if (time.time() > self.last_question_refresh_time + self.refresh_time_seconds):
            self.bot.loop.create_task(self.load_questions())

        if (len(self.questions) > 0):
            return random.choice(self.questions)
        return None


    @commands.command(name="stupidquestion", brief="Ask a stupid question, via Reddit.")
    async def stupid_question(self, ctx):
        question = self.get_question()

        if (question):
            say_result = await self.hawking.get_speech_cog()._say(ctx, question.text, ignore_char_limit = True)
            if (say_result):
                embedded_question = discord.Embed(description="{}\n\nvia [/r/{}]({})".format(question.text, question.subreddit, question.url))

                await ctx.send("Hey <@{}>, {}".format(
                    ctx.message.author.id,
                    random.choice(self.THOUGHT_PROVOKING_STRINGS),
                ),
                    embed=embedded_question
                )
        else:
            await ctx.send("Sorry <@{}>, but I'm having trouble loading questions from Reddit. Try again in a bit.".format(ctx.message.author.id))


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(StupidQuestions, dependencies=["Reddit"])
